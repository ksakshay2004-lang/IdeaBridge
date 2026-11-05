"""Idea privacy is the most security-critical behaviour: test the full visibility matrix."""
from conftest import hdr


def _collab(client, ent, idea_id, msg="We would like to collaborate on this idea."):
    return client.post("/api/collaboration", json={"idea_id": idea_id, "message": msg}, headers=ent["h"])


def test_create_triggers_completed_demo_evaluation(client, signup, make_idea):
    cre = signup("creator")
    idea = make_idea(cre)
    ev = client.get(f"/api/ideas/{idea['id']}/evaluation", headers=cre["h"]).json()["current"]
    assert ev["status"] == "completed" and ev["mode"] == "demo"
    rep = ev["report"]
    assert "DEMO MODE" in rep["meta"]["notice"]
    assert all(0 <= v <= 100 for v in rep["scores"].values())
    assert rep["similar_projects"], "should retrieve curated references"


def test_public_idea_visibility(client, signup, make_idea):
    cre, ent = signup("creator"), signup("entrepreneur")
    idea = make_idea(cre, visibility="public")
    anon = client.get(f"/api/ideas/{idea['id']}").json()
    assert anon["access"] == "teaser" and "problem" not in anon and "documents" not in anon
    full = client.get(f"/api/ideas/{idea['id']}", headers=ent["h"]).json()
    assert full["access"] == "full" and "problem" in full
    assert client.get(f"/api/ideas/{idea['id']}/evaluation", headers=ent["h"]).status_code == 200
    assert client.get(f"/api/ideas/{idea['id']}/evaluation").status_code == 403  # anonymous


def test_restricted_idea_teaser_until_request_accepted(client, signup, make_idea):
    cre, ent, other = signup("creator"), signup("entrepreneur"), signup("entrepreneur")
    idea = make_idea(cre, visibility="restricted")
    iid = idea["id"]
    assert client.get(f"/api/ideas/{iid}").status_code == 404  # anonymous cannot even see it exists
    teaser = client.get(f"/api/ideas/{iid}", headers=ent["h"]).json()
    assert teaser["access"] == "teaser" and "problem" not in teaser and teaser["scores"] is None
    assert client.get(f"/api/ideas/{iid}/evaluation", headers=ent["h"]).status_code == 403
    rid = _collab(client, ent, iid).json()["id"]
    assert client.get(f"/api/ideas/{iid}", headers=ent["h"]).json()["access"] == "teaser"  # pending != access
    client.post(f"/api/collaboration/{rid}/respond", json={"action": "accept"}, headers=cre["h"])
    assert client.get(f"/api/ideas/{iid}", headers=ent["h"]).json()["access"] == "full"
    assert client.get(f"/api/ideas/{iid}/evaluation", headers=ent["h"]).status_code == 200
    assert client.get(f"/api/ideas/{iid}", headers=other["h"]).json()["access"] == "teaser"  # grant is per-person


def test_private_idea_hidden_from_everyone_but_owner_and_admin(client, signup, make_idea, admin):
    cre, ent = signup("creator"), signup("entrepreneur")
    iid = make_idea(cre, visibility="private")["id"]
    assert client.get(f"/api/ideas/{iid}").status_code == 404
    assert client.get(f"/api/ideas/{iid}", headers=ent["h"]).status_code == 404
    assert client.get(f"/api/ideas/{iid}/evaluation", headers=ent["h"]).status_code == 404
    assert _collab(client, ent, iid).status_code == 404
    assert client.post(f"/api/saved/{iid}", headers=ent["h"]).status_code == 404
    assert client.get(f"/api/ideas/{iid}", headers=cre["h"]).status_code == 200
    assert client.get(f"/api/ideas/{iid}", headers=admin["h"]).status_code == 200
    listing = client.get("/api/ideas?page_size=50", headers=ent["h"]).json()["items"]
    assert iid not in [i["id"] for i in listing]


def test_explore_hides_restricted_from_anonymous_and_shows_teasers_to_users(client, signup, make_idea):
    cre, ent = signup("creator"), signup("entrepreneur")
    pub = make_idea(cre, visibility="public", title="Public unique-marker idea alpha")["id"]
    res = make_idea(cre, visibility="restricted", title="Restricted unique-marker idea alpha")["id"]
    anon = {i["id"] for i in client.get("/api/ideas?q=unique-marker&page_size=50").json()["items"]}
    assert pub in anon and res not in anon
    user_items = {i["id"]: i for i in client.get("/api/ideas?q=unique-marker&page_size=50", headers=ent["h"]).json()["items"]}
    assert pub in user_items and res in user_items
    assert user_items[res]["access"] == "teaser" and "problem" not in user_items[res]


def test_only_owner_can_edit_or_delete(client, signup, make_idea):
    cre, other = signup("creator"), signup("creator")
    iid = make_idea(cre)["id"]
    assert client.put(f"/api/ideas/{iid}", json={"stage": "mvp"}, headers=other["h"]).status_code == 404
    assert client.delete(f"/api/ideas/{iid}", headers=other["h"]).status_code == 404
    r = client.put(f"/api/ideas/{iid}", json={"stage": "mvp", "visibility": "private"}, headers=cre["h"])
    assert r.status_code == 200 and r.json()["stage"] == "mvp" and r.json()["visibility"] == "private"
    assert client.delete(f"/api/ideas/{iid}", headers=cre["h"]).status_code == 204
    assert client.get(f"/api/ideas/{iid}", headers=cre["h"]).status_code == 404


def test_validation_and_unknown_industry(client, signup):
    from conftest import IDEA
    cre = signup("creator")
    assert client.post("/api/ideas", json={**IDEA, "title": "x"}, headers=cre["h"]).status_code == 422
    assert client.post("/api/ideas", json={**IDEA, "industry": "Underwater Basketry"}, headers=cre["h"]).status_code == 422
    assert client.post("/api/ideas", json={**IDEA, "visibility": "secret"}, headers=cre["h"]).status_code == 422


def test_entrepreneur_cannot_submit_ideas(client, signup):
    from conftest import IDEA
    assert client.post("/api/ideas", json=IDEA, headers=signup("entrepreneur")["h"]).status_code == 403


def test_hidden_by_moderation_is_invisible_to_others(client, signup, make_idea, admin):
    cre, ent = signup("creator"), signup("entrepreneur")
    iid = make_idea(cre)["id"]
    client.patch(f"/api/admin/ideas/{iid}", json={"moderation_status": "hidden"}, headers=admin["h"])
    assert client.get(f"/api/ideas/{iid}", headers=ent["h"]).status_code == 404
    assert client.get(f"/api/ideas/{iid}", headers=cre["h"]).status_code == 200  # owner still sees it
