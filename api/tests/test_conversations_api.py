from app.auth.csrf import CSRF_HEADER_NAME
from app.config import settings


def _login(client, seed_user):
    user_id = seed_user(email="analyst@example.com", password="correct-horse-battery")
    client.post(
        "/v1/auth/login",
        json={"email": "analyst@example.com", "password": "correct-horse-battery"},
    )
    headers = {CSRF_HEADER_NAME: client.cookies[settings.csrf_cookie_name]}
    return user_id, headers


def test_list_conversations_pinned_first(client, seed_user, seed_conversation):
    user_id, headers = _login(client, seed_user)
    seed_conversation(user_id, title="Unpinned older", pinned=False)
    pinned_id = seed_conversation(user_id, title="Pinned one", pinned=True)

    resp = client.get("/v1/conversations")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["conversation_id"] == pinned_id
    assert body[0]["pinned"] is True


def test_list_conversations_scoped_to_caller(client, seed_user, seed_conversation):
    user_id, headers = _login(client, seed_user)
    other_user_id = seed_user(email="other@example.com", password="correct-horse-battery")
    seed_conversation(other_user_id, title="Someone else's conversation")

    resp = client.get("/v1/conversations")
    assert resp.status_code == 200
    assert resp.json() == []


def test_rename_and_pin_conversation(client, seed_user, seed_conversation):
    user_id, headers = _login(client, seed_user)
    conversation_id = seed_conversation(user_id, title="Original title", pinned=False)

    resp = client.patch(
        f"/v1/conversations/{conversation_id}",
        json={"pinned": True, "title": "Renamed"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["pinned"] is True
    assert body["title"] == "Renamed"


def test_patch_unknown_conversation_404(client, seed_user):
    _, headers = _login(client, seed_user)
    resp = client.patch(
        "/v1/conversations/00000000-0000-0000-0000-000000000000",
        json={"pinned": True},
        headers=headers,
    )
    assert resp.status_code == 404


def test_delete_conversation(client, seed_user, seed_conversation):
    user_id, headers = _login(client, seed_user)
    conversation_id = seed_conversation(user_id)

    resp = client.delete(f"/v1/conversations/{conversation_id}", headers=headers)
    assert resp.status_code == 204
    assert client.get("/v1/conversations").json() == []


def test_delete_unknown_conversation_404(client, seed_user):
    _, headers = _login(client, seed_user)
    resp = client.delete("/v1/conversations/00000000-0000-0000-0000-000000000000", headers=headers)
    assert resp.status_code == 404


def test_delete_other_callers_conversation_404(client, seed_user, seed_conversation):
    other_user_id = seed_user(email="other@example.com", password="correct-horse-battery")
    other_conversation_id = seed_conversation(other_user_id)

    _, headers = _login(client, seed_user)
    resp = client.delete(f"/v1/conversations/{other_conversation_id}", headers=headers)
    assert resp.status_code == 404


def test_conversations_require_auth(client):
    resp = client.get("/v1/conversations")
    assert resp.status_code == 401
