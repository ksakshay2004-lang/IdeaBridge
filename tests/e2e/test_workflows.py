"""API-level end-to-end journey covering the essential product workflow (no browser required)."""
import io

from conftest import IDEA


def test_full_marketplace_journey(client, signup, admin):
    # 1. Creator registers, completes profile, submits a RESTRICTED idea with a document
    creator = signup("creator", "Priya Sharma")
    assert client.put("/api/profile/me/creator", headers=creator["h"], json={
        "headline": "CS student", "skills": ["python", "ml"], "website": "https://example.org"}).status_code == 200
    idea = client.post("/api/ideas", headers=creator["h"], json={**IDEA, "visibility": "restricted"}).json()["idea"]
    iid = idea["id"]
    doc = client.post(f"/api/ideas/{iid}/documents", headers=creator["h"],
                      files={"file": ("pitch.txt", io.BytesIO(b"pitch notes"), "text/plain")})
    assert doc.status_code == 201

    # 2. AI evaluation completed and is clearly labelled as demo
    ev = client.get(f"/api/ideas/{iid}/evaluation", headers=creator["h"]).json()["current"]
    assert ev["status"] == "completed" and ev["report"]["meta"]["mode"] == "demo"
    assert {"technical_feasibility", "market_opportunity", "innovation_differentiation"} <= ev["report"]["scores"].keys()
    assert any(n["kind"] == "evaluation_done" for n in client.get("/api/notifications", headers=creator["h"]).json())

    # 3. Entrepreneur registers, sets profile, gets verified by admin
    ent = signup("entrepreneur", "Daniel Cho", company="Sample Capital")
    client.put("/api/profile/me/entrepreneur", headers=ent["h"], json={
        "company_name": "Sample Capital", "company_type": "investor", "industries": ["EdTech"],
        "technologies": ["Mobile App"], "interests": "offline learning flashcards", "preferred_stages": ["prototype"],
        "investment_min": 10000, "investment_max": 100000})
    client.patch(f"/api/admin/users/{ent['user']['id']}", json={"is_verified": True}, headers=admin["h"])

    # 4. Discovery: search, filter, recommendation; restricted idea only a teaser
    found = client.get("/api/ideas?q=flashcards&industry=EdTech", headers=ent["h"]).json()["items"]
    card = next(i for i in found if i["id"] == iid)
    assert card["access"] == "teaser" and "problem" not in card
    sem = client.get("/api/ideas?q=study cards for students without internet&semantic=true", headers=ent["h"]).json()
    assert sem["total"] >= 1
    assert iid in [i["id"] for i in client.get("/api/recommendations", headers=ent["h"]).json()]
    assert client.post(f"/api/saved/{iid}", headers=ent["h"]).status_code == 201

    # 5. Collaboration request, creator accepts -> entrepreneur unlocks report and document
    req = client.post("/api/collaboration", headers=ent["h"], json={"idea_id": iid, "kind": "fund",
                                                                    "message": "We would like to fund a pilot."}).json()
    assert client.get(f"/api/ideas/{iid}/evaluation", headers=ent["h"]).status_code == 403
    client.post(f"/api/collaboration/{req['id']}/respond", headers=creator["h"], json={"action": "accept", "message": "Welcome"})
    full = client.get(f"/api/ideas/{iid}", headers=ent["h"]).json()
    assert full["access"] == "full" and full["documents"][0]["filename"] == "pitch.txt"
    assert client.get(f"/api/ideas/{iid}/evaluation", headers=ent["h"]).status_code == 200
    assert client.get(f"/api/documents/{full['documents'][0]['id']}/download", headers=ent["h"]).content == b"pitch notes"

    # 6. Messaging both ways
    assert client.post("/api/messages", headers=ent["h"], json={"recipient_id": creator["user"]["id"], "body": "Can we call on Monday?", "idea_id": iid}).status_code == 201
    assert client.post("/api/messages", headers=creator["h"], json={"recipient_id": ent["user"]["id"], "body": "Monday works."}).status_code == 201
    thread = client.get(f"/api/messages/thread/{creator['user']['id']}", headers=ent["h"]).json()
    assert [m["body"] for m in thread["messages"]] == ["Can we call on Monday?", "Monday works."]

    # 7. Creator edits the idea; the report is flagged outdated until re-run
    client.put(f"/api/ideas/{iid}", headers=creator["h"], json={"stage": "mvp", "solution": IDEA["solution"] + " Now with teacher dashboards."})
    assert client.post(f"/api/ideas/{iid}/evaluate", headers=creator["h"]).status_code == 202
    assert client.get(f"/api/ideas/{iid}/evaluation", headers=creator["h"]).json()["current"]["version"] == 2

    # 8. Admin sees it all in analytics; creator deletes the idea
    a = client.get("/api/admin/analytics", headers=admin["h"]).json()
    assert a["totals"]["ideas"] >= 1 and a["totals"]["collab_requests"] >= 1
    assert client.delete(f"/api/ideas/{iid}", headers=creator["h"]).status_code == 204
    assert client.get(f"/api/documents/{full['documents'][0]['id']}/download", headers=ent["h"]).status_code == 404
