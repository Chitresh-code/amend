from app.auth.csrf import CSRF_HEADER_NAME
from app.config import settings


def _login(client, seed_user):
    seed_user(email="analyst@example.com", password="correct-horse-battery")
    client.post(
        "/v1/auth/login",
        json={"email": "analyst@example.com", "password": "correct-horse-battery"},
    )
    return {CSRF_HEADER_NAME: client.cookies[settings.csrf_cookie_name]}


def test_create_credential_requires_csrf_header(client, seed_user):
    _login(client, seed_user)

    resp = client.post(
        "/v1/credentials",
        json={"provider": "anthropic", "model_id": "claude-sonnet-4-5", "api_key": "sk-ant-x"},
    )

    assert resp.status_code == 403


def test_create_and_list_credential(client, seed_user):
    headers = _login(client, seed_user)

    create_resp = client.post(
        "/v1/credentials",
        json={"provider": "anthropic", "model_id": "claude-sonnet-4-5", "api_key": "sk-ant-wxyz"},
        headers=headers,
    )
    assert create_resp.status_code == 200
    body = create_resp.json()
    assert body["provider"] == "anthropic"
    assert body["key_suffix"] == "wxyz"
    assert body["is_default"] is True
    assert "api_key" not in body

    list_resp = client.get("/v1/credentials")
    assert list_resp.status_code == 200
    listed = list_resp.json()
    assert len(listed) == 1
    assert listed[0]["provider"] == "anthropic"


def test_second_credential_is_not_default(client, seed_user):
    headers = _login(client, seed_user)
    client.post(
        "/v1/credentials",
        json={"provider": "anthropic", "model_id": "claude-sonnet-4-5", "api_key": "sk-ant-wxyz"},
        headers=headers,
    )

    resp = client.post(
        "/v1/credentials",
        json={"provider": "openai", "model_id": "gpt-5", "api_key": "sk-oai-abcd"},
        headers=headers,
    )

    assert resp.status_code == 200
    assert resp.json()["is_default"] is False


def test_set_default_clears_previous_default(client, seed_user):
    headers = _login(client, seed_user)
    client.post(
        "/v1/credentials",
        json={"provider": "anthropic", "model_id": "claude-sonnet-4-5", "api_key": "sk-ant-wxyz"},
        headers=headers,
    )
    client.post(
        "/v1/credentials",
        json={"provider": "openai", "model_id": "gpt-5", "api_key": "sk-oai-abcd"},
        headers=headers,
    )

    resp = client.patch("/v1/credentials/openai", json={"is_default": True}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_default"] is True

    listed = {c["provider"]: c["is_default"] for c in client.get("/v1/credentials").json()}
    assert listed == {"anthropic": False, "openai": True}


def test_delete_credential(client, seed_user):
    headers = _login(client, seed_user)
    client.post(
        "/v1/credentials",
        json={"provider": "anthropic", "model_id": "claude-sonnet-4-5", "api_key": "sk-ant-wxyz"},
        headers=headers,
    )

    resp = client.delete("/v1/credentials/anthropic", headers=headers)
    assert resp.status_code == 204
    assert client.get("/v1/credentials").json() == []


def test_delete_unknown_credential_404(client, seed_user):
    headers = _login(client, seed_user)
    resp = client.delete("/v1/credentials/anthropic", headers=headers)
    assert resp.status_code == 404


def test_create_credential_rejects_unsupported_provider(client, seed_user):
    headers = _login(client, seed_user)
    resp = client.post(
        "/v1/credentials",
        json={"provider": "not-a-real-provider", "model_id": "x", "api_key": "y"},
        headers=headers,
    )
    assert resp.status_code == 400


def test_credentials_require_auth(client):
    resp = client.get("/v1/credentials")
    assert resp.status_code == 401
