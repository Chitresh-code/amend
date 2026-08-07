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


def test_list_api_keys(client, seed_user, seed_api_key):
    user_id, _ = _login(client, seed_user)
    seed_api_key(user_id, label="Production", raw_key="sk-amd-abcd1234")

    resp = client.get("/v1/api-keys")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["label"] == "Production"
    assert body[0]["key_suffix"] == "1234"


def test_list_api_keys_scoped_to_caller(client, seed_user, seed_api_key):
    user_id, _ = _login(client, seed_user)
    other_user_id = seed_user(email="other@example.com", password="correct-horse-battery")
    seed_api_key(other_user_id)

    resp = client.get("/v1/api-keys")
    assert resp.status_code == 200
    assert resp.json() == []


def test_revoke_api_key(client, seed_user, seed_api_key):
    user_id, headers = _login(client, seed_user)
    key_id = seed_api_key(user_id)

    resp = client.delete(f"/v1/api-keys/{key_id}", headers=headers)
    assert resp.status_code == 204
    assert client.get("/v1/api-keys").json() == []


def test_revoke_already_revoked_key_404(client, seed_user, seed_api_key):
    user_id, headers = _login(client, seed_user)
    key_id = seed_api_key(user_id)
    client.delete(f"/v1/api-keys/{key_id}", headers=headers)

    resp = client.delete(f"/v1/api-keys/{key_id}", headers=headers)
    assert resp.status_code == 404


def test_revoke_other_callers_key_404(client, seed_user, seed_api_key):
    other_user_id = seed_user(email="other@example.com", password="correct-horse-battery")
    other_key_id = seed_api_key(other_user_id)

    _, headers = _login(client, seed_user)
    resp = client.delete(f"/v1/api-keys/{other_key_id}", headers=headers)
    assert resp.status_code == 404


def test_api_keys_require_auth(client):
    resp = client.get("/v1/api-keys")
    assert resp.status_code == 401
