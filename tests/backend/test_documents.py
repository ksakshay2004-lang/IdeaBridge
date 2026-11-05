import io

from conftest import hdr


def _upload(client, owner, iid, name="notes.txt", data=b"hello world", ctype="text/plain"):
    return client.post(f"/api/ideas/{iid}/documents", files={"file": (name, io.BytesIO(data), ctype)}, headers=owner["h"])


def test_upload_download_and_delete(client, signup, make_idea):
    cre, ent = signup("creator"), signup("entrepreneur")
    iid = make_idea(cre, visibility="public")["id"]
    r = _upload(client, cre, iid)
    assert r.status_code == 201, r.text
    did = r.json()["id"]
    assert client.get(f"/api/documents/{did}/download", headers=cre["h"]).content == b"hello world"
    assert client.get(f"/api/documents/{did}/download", headers=ent["h"]).status_code == 200  # public => full access
    assert client.get(f"/api/documents/{did}/download").status_code == 401
    assert client.delete(f"/api/documents/{did}", headers=ent["h"]).status_code == 403
    assert client.delete(f"/api/documents/{did}", headers=cre["h"]).status_code == 204


def test_restricted_documents_protected(client, signup, make_idea):
    cre, ent = signup("creator"), signup("entrepreneur")
    iid = make_idea(cre, visibility="restricted")["id"]
    did = _upload(client, cre, iid).json()["id"]
    assert client.get(f"/api/documents/{did}/download", headers=ent["h"]).status_code == 404
    rid = client.post("/api/collaboration", json={"idea_id": iid, "message": "Let us talk about this idea."},
                      headers=ent["h"]).json()["id"]
    client.post(f"/api/collaboration/{rid}/respond", json={"action": "accept"}, headers=cre["h"])
    assert client.get(f"/api/documents/{did}/download", headers=ent["h"]).status_code == 200


def test_upload_restrictions(client, signup, make_idea):
    cre, other = signup("creator"), signup("creator")
    iid = make_idea(cre)["id"]
    assert _upload(client, cre, iid, "evil.exe", b"MZ...").status_code == 415
    assert _upload(client, cre, iid, "fake.pdf", b"not a pdf").status_code == 415           # magic-byte mismatch
    assert _upload(client, cre, iid, "ok.pdf", b"%PDF-1.4 minimal").status_code == 201
    assert _upload(client, cre, iid, "big.txt", b"a" * (1024 * 1024 + 10)).status_code == 413
    assert _upload(client, cre, iid, "empty.txt", b"").status_code == 400
    assert _upload(client, other, iid).status_code == 404                                    # not the owner
    r = _upload(client, cre, iid, "../../etc/passwd.txt", b"x")
    assert r.status_code == 201 and "/" not in r.json()["filename"]
