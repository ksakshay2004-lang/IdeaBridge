import uuid

from conftest import PASSWORD, hdr


def test_register_login_me_roundtrip(client, signup):
    u = signup("creator", "Ada Lovelace")
    assert u["user"]["role"] == "creator"
    assert "password" not in str(u["user"]).lower()
    r = client.post("/api/auth/login", json={"email": u["email"], "password": PASSWORD})
    assert r.status_code == 200
    me = client.get("/api/auth/me", headers=hdr(r.json()["access_token"]))
    assert me.status_code == 200 and me.json()["email"] == u["email"]


def test_duplicate_email_conflict(client, signup):
    u = signup("creator")
    r = client.post("/api/auth/register", json={"email": u["email"].upper(), "password": PASSWORD,
                                                "full_name": "Dup Licate", "role": "creator"})
    assert r.status_code == 409


def test_weak_passwords_rejected(client):
    for pw in ("short1", "alllettersnodigits", "12345678901"):
        r = client.post("/api/auth/register", json={"email": f"{uuid.uuid4().hex[:8]}@ideabridge.io", "password": pw,
                                                    "full_name": "Weak Pass", "role": "creator"})
        assert r.status_code == 422, pw


def test_cannot_self_register_as_admin(client):
    r = client.post("/api/auth/register", json={"email": f"{uuid.uuid4().hex[:8]}@ideabridge.io", "password": PASSWORD,
                                                "full_name": "Evil Admin", "role": "admin"})
    assert r.status_code == 422


def test_wrong_password_and_unknown_user_same_error(client, signup):
    u = signup("creator")
    a = client.post("/api/auth/login", json={"email": u["email"], "password": "Wrong#12345"})
    b = client.post("/api/auth/login", json={"email": "nobody@ideabridge.io", "password": "Wrong#12345"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()


def test_protected_routes_need_token_and_reject_garbage(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=hdr("not.a.jwt")).status_code == 401
    assert client.get("/api/ideas/mine").status_code == 401


def test_role_enforcement(client, signup):
    ent, cre = signup("entrepreneur"), signup("creator")
    assert client.get("/api/ideas/mine", headers=ent["h"]).status_code == 403
    assert client.get("/api/saved", headers=cre["h"]).status_code == 403
    assert client.get("/api/admin/analytics", headers=cre["h"]).status_code == 403


def test_change_password(client, signup):
    u = signup("creator")
    bad = client.post("/api/auth/change-password", headers=u["h"],
                      json={"current_password": "nope12345", "new_password": "Newpass#123"})
    assert bad.status_code == 400
    ok = client.post("/api/auth/change-password", headers=u["h"],
                     json={"current_password": PASSWORD, "new_password": "Newpass#123"})
    assert ok.status_code == 200
    assert client.post("/api/auth/login", json={"email": u["email"], "password": PASSWORD}).status_code == 401
    assert client.post("/api/auth/login", json={"email": u["email"], "password": "Newpass#123"}).status_code == 200


def test_login_throttle(client):
    email = f"{uuid.uuid4().hex[:8]}@ideabridge.io"
    codes = [client.post("/api/auth/login", json={"email": email, "password": "Bad#password1"}).status_code
             for _ in range(10)]
    assert codes[0] == 401 and codes[-1] == 429


def test_deactivated_user_blocked(client, signup, admin):
    u = signup("creator")
    r = client.patch(f"/api/admin/users/{u['user']['id']}", json={"is_active": False}, headers=admin["h"])
    assert r.status_code == 200
    assert client.get("/api/auth/me", headers=u["h"]).status_code == 401  # existing token stops working
    assert client.post("/api/auth/login", json={"email": u["email"], "password": PASSWORD}).status_code == 403
