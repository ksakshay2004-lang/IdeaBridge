from conftest import hdr


def _req(client, ent, iid, kind="collaborate"):
    return client.post("/api/collaboration", json={"idea_id": iid, "kind": kind, "message": "Interested in working together."},
                       headers=ent["h"])


def test_collaboration_lifecycle_and_notifications(client, signup, make_idea):
    cre, ent = signup("creator"), signup("entrepreneur", company="Acme Ventures")
    iid = make_idea(cre)["id"]
    r = _req(client, ent, iid, "fund")
    assert r.status_code == 201 and r.json()["status"] == "pending"
    assert _req(client, ent, iid).status_code == 409
    assert client.post(f"/api/collaboration/{r.json()['id']}/respond", json={"action": "accept"}, headers=ent["h"]).status_code == 403
    inbox = client.get("/api/collaboration", headers=cre["h"]).json()
    assert [x["id"] for x in inbox] == [r.json()["id"]]
    assert client.get("/api/notifications/unread-count", headers=cre["h"]).json()["notifications"] >= 1
    done = client.post(f"/api/collaboration/{r.json()['id']}/respond", json={"action": "accept", "message": "Great"}, headers=cre["h"])
    assert done.json()["status"] == "accepted"
    assert client.post(f"/api/collaboration/{r.json()['id']}/respond", json={"action": "decline"}, headers=cre["h"]).status_code == 409
    notes = client.get("/api/notifications", headers=ent["h"]).json()
    assert any(n["kind"] == "collab_accepted" for n in notes)
    assert client.post(f"/api/notifications/{notes[0]['id']}/read", headers=ent["h"]).status_code == 200
    assert client.post(f"/api/notifications/{notes[0]['id']}/read", headers=cre["h"]).status_code == 404  # not yours


def test_other_creator_cannot_respond(client, signup, make_idea):
    cre, other, ent = signup("creator"), signup("creator"), signup("entrepreneur")
    rid = _req(client, ent, make_idea(cre)["id"]).json()["id"]
    assert client.post(f"/api/collaboration/{rid}/respond", json={"action": "accept"}, headers=other["h"]).status_code == 404


def test_withdraw_then_request_again(client, signup, make_idea):
    cre, ent = signup("creator"), signup("entrepreneur")
    iid = make_idea(cre)["id"]
    rid = _req(client, ent, iid).json()["id"]
    assert client.post(f"/api/collaboration/{rid}/withdraw", headers=ent["h"]).json()["status"] == "withdrawn"
    assert _req(client, ent, iid).status_code == 201


def test_messaging_rules_and_read_state(client, signup):
    cre, ent, stranger = signup("creator"), signup("entrepreneur"), signup("entrepreneur")
    assert client.post("/api/messages", json={"recipient_id": ent["user"]["id"], "body": "cold outreach"}, headers=cre["h"]).status_code == 403
    assert client.post("/api/messages", json={"recipient_id": cre["user"]["id"], "body": "Hello, saw your idea."}, headers=ent["h"]).status_code == 201
    assert client.get("/api/notifications/unread-count", headers=cre["h"]).json()["messages"] == 1
    conv = client.get("/api/messages/conversations", headers=cre["h"]).json()
    assert conv[0]["user_id"] == ent["user"]["id"] and conv[0]["unread"] == 1
    t = client.get(f"/api/messages/thread/{ent['user']['id']}", headers=cre["h"]).json()
    assert t["can_send"] is True and len(t["messages"]) == 1
    assert client.get("/api/notifications/unread-count", headers=cre["h"]).json()["messages"] == 0
    assert client.post("/api/messages", json={"recipient_id": ent["user"]["id"], "body": "Thanks, let us talk."}, headers=cre["h"]).status_code == 201
    third = client.get(f"/api/messages/thread/{cre['user']['id']}", headers=stranger["h"]).json()
    assert third["messages"] == []                                   # strangers cannot read other threads
    assert client.post("/api/messages", json={"recipient_id": cre["user"]["id"], "body": ""}, headers=ent["h"]).status_code == 422


def test_save_unsave_and_saved_list(client, signup, make_idea):
    cre, ent = signup("creator"), signup("entrepreneur")
    iid = make_idea(cre)["id"]
    assert client.post(f"/api/saved/{iid}", headers=ent["h"]).status_code == 201
    assert client.post(f"/api/saved/{iid}", headers=ent["h"]).status_code == 201  # idempotent
    assert [i["id"] for i in client.get("/api/saved", headers=ent["h"]).json()] == [iid]
    assert client.get(f"/api/ideas/{iid}", headers=ent["h"]).json()["is_saved"] is True
    client.delete(f"/api/saved/{iid}", headers=ent["h"])
    assert client.get("/api/saved", headers=ent["h"]).json() == []


def test_recommendations_and_creator_side_matches(client, signup, make_idea):
    cre, ent = signup("creator"), signup("entrepreneur", company="Match Co")
    iid = make_idea(cre)["id"]
    r = client.put("/api/profile/me/entrepreneur", headers=ent["h"], json={
        "company_name": "Match Co", "company_type": "investor", "industries": ["EdTech"], "technologies": ["Mobile App"],
        "interests": "spaced repetition flashcards offline learning", "preferred_stages": ["prototype"],
        "target_markets": ["students"], "investment_min": 10000, "investment_max": 100000})
    assert r.status_code == 200
    recs = client.get("/api/recommendations", headers=ent["h"]).json()
    mine = next(i for i in recs if i["id"] == iid)
    assert mine["match"]["score"] >= 70 and mine["match"]["reasons"]
    assert recs[0]["match"]["score"] >= recs[-1]["match"]["score"]
    matches = client.get(f"/api/ideas/{iid}/matches", headers=cre["h"]).json()
    assert any(m["entrepreneur"]["id"] == ent["user"]["id"] for m in matches)
    assert client.get(f"/api/ideas/{iid}/matches", headers=ent["h"]).status_code == 404


def test_profile_validation(client, signup):
    ent = signup("entrepreneur")
    bad = client.put("/api/profile/me/entrepreneur", headers=ent["h"], json={"investment_min": 500, "investment_max": 100})
    assert bad.status_code == 422
    assert client.put("/api/profile/me/creator", headers=ent["h"], json={"headline": "x"}).status_code == 403
    cre = signup("creator")
    assert client.put("/api/profile/me/creator", headers=cre["h"], json={"website": "javascript:alert(1)"}).status_code == 422


def test_admin_user_management_and_verification(client, signup, admin):
    ent = signup("entrepreneur")
    users = client.get("/api/admin/users?role=entrepreneur", headers=admin["h"]).json()
    assert users["total"] >= 1
    r = client.patch(f"/api/admin/users/{ent['user']['id']}", json={"is_verified": True}, headers=admin["h"])
    assert r.json()["is_verified"] is True
    assert client.get("/api/auth/me", headers=ent["h"]).json()["is_verified"] is True
    assert client.patch(f"/api/admin/users/{admin['user']['id']}", json={"is_active": False}, headers=admin["h"]).status_code == 400
    assert client.delete(f"/api/admin/users/{admin['user']['id']}", headers=admin["h"]).status_code == 400
    logs = client.get("/api/admin/logs", headers=admin["h"]).json()
    assert any(l["action"] == "user_verify" for l in logs)


def test_admin_categories_crud_and_idea_industry_rules(client, signup, admin):
    cre = signup("creator")
    from conftest import IDEA
    c = client.post("/api/admin/categories", json={"name": "SpaceTech", "kind": "industry"}, headers=admin["h"])
    assert c.status_code == 201
    assert client.post("/api/admin/categories", json={"name": "spacetech", "kind": "industry"}, headers=admin["h"]).status_code == 409
    assert client.post("/api/ideas", json={**IDEA, "industry": "SpaceTech"}, headers=cre["h"]).status_code == 201
    assert client.delete(f"/api/admin/categories/{c.json()['id']}", headers=admin["h"]).status_code == 409  # in use
    client.patch(f"/api/admin/categories/{c.json()['id']}", json={"is_active": False}, headers=admin["h"])
    assert "SpaceTech" not in [i["name"] for i in client.get("/api/categories").json()["industries"]]
    assert client.post("/api/ideas", json={**IDEA, "industry": "SpaceTech"}, headers=cre["h"]).status_code == 422


def test_report_moderation_flow(client, signup, make_idea, admin):
    cre, ent = signup("creator"), signup("entrepreneur")
    iid = make_idea(cre, title="Reportable idea marker zz")["id"]
    assert client.post(f"/api/ideas/{iid}/report", json={"reason": "spam"}, headers=cre["h"]).status_code == 400
    assert client.post(f"/api/ideas/{iid}/report", json={"reason": "spam", "details": "looks like spam"}, headers=ent["h"]).status_code == 201
    assert client.post(f"/api/ideas/{iid}/report", json={"reason": "spam"}, headers=ent["h"]).status_code == 409
    reports = client.get("/api/admin/reports", headers=admin["h"]).json()
    rep = next(r for r in reports if r["idea"]["id"] == iid)
    assert client.post(f"/api/admin/reports/{rep['id']}/resolve", json={"action": "hide_idea", "note": "spam"}, headers=admin["h"]).status_code == 200
    assert client.get(f"/api/ideas/{iid}", headers=ent["h"]).status_code == 404
    assert any(n["kind"] == "moderation" for n in client.get("/api/notifications", headers=cre["h"]).json())
    assert client.post(f"/api/admin/reports/{rep['id']}/resolve", json={"action": "dismiss"}, headers=admin["h"]).status_code == 409


def test_admin_analytics_shape(client, admin):
    a = client.get("/api/admin/analytics", headers=admin["h"]).json()
    assert {"totals", "growth", "ideas_by_industry", "avg_scores", "collab_by_status"} <= a.keys()
    assert len(a["growth"]["labels"]) == 14 == len(a["growth"]["users"])
    assert a["totals"]["reference_projects"] > 0 and a["totals"]["evaluations_live"] == 0
