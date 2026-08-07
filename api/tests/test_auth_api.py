from app.config import settings


def test_login_success_sets_cookies(client, seed_user):
    seed_user(email="analyst@example.com", password="correct-horse-battery")

    resp = client.post(
        "/v1/auth/login",
        json={"email": "analyst@example.com", "password": "correct-horse-battery"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "analyst@example.com"
    assert body["organization"] == "Example Bank"
    assert settings.session_cookie_name in resp.cookies
    assert settings.csrf_cookie_name in resp.cookies


def test_login_wrong_password(client, seed_user):
    seed_user(email="analyst@example.com", password="correct-horse-battery")

    resp = client.post(
        "/v1/auth/login", json={"email": "analyst@example.com", "password": "wrong-password"}
    )

    assert resp.status_code == 401


def test_login_unknown_email(client):
    resp = client.post(
        "/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever"}
    )

    assert resp.status_code == 401


def test_session_requires_auth(client):
    resp = client.get("/v1/auth/session")
    assert resp.status_code == 401


def test_session_with_valid_cookie(client, seed_user):
    seed_user(email="analyst@example.com", password="correct-horse-battery")
    client.post(
        "/v1/auth/login",
        json={"email": "analyst@example.com", "password": "correct-horse-battery"},
    )

    resp = client.get("/v1/auth/session")

    assert resp.status_code == 200
    assert resp.json()["email"] == "analyst@example.com"


def test_logout_revokes_session(client, seed_user):
    seed_user(email="analyst@example.com", password="correct-horse-battery")
    client.post(
        "/v1/auth/login",
        json={"email": "analyst@example.com", "password": "correct-horse-battery"},
    )

    logout_resp = client.post("/v1/auth/logout")
    assert logout_resp.status_code == 204

    resp = client.get("/v1/auth/session")
    assert resp.status_code == 401


def test_login_rate_limited_by_ip(client, seed_user):
    seed_user(email="analyst@example.com", password="correct-horse-battery")

    for _ in range(settings.login_rate_limit_attempts):
        resp = client.post(
            "/v1/auth/login", json={"email": "analyst@example.com", "password": "wrong"}
        )
        assert resp.status_code == 401

    resp = client.post("/v1/auth/login", json={"email": "analyst@example.com", "password": "wrong"})
    assert resp.status_code == 429
