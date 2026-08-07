from app.auth.csrf import CSRF_HEADER_NAME
from app.config import settings


def _login(client, seed_user):
    seed_user(email="analyst@example.com", password="correct-horse-battery")
    client.post(
        "/v1/auth/login",
        json={"email": "analyst@example.com", "password": "correct-horse-battery"},
    )
    return {CSRF_HEADER_NAME: client.cookies[settings.csrf_cookie_name]}


def test_register_and_list_embedding_index(client, seed_user):
    headers = _login(client, seed_user)

    resp = client.post(
        "/v1/embedding-indexes",
        json={"provider": "voyage", "model_id": "voyage-law-2", "dimension": 1024},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["embedding_model_id"] == "voyage:voyage-law-2"
    assert body["status"] == "registered"
    assert body["clause_count"] == 0
    assert body["is_default"] is False

    listed = client.get("/v1/embedding-indexes").json()
    assert len(listed) == 1
    assert listed[0]["embedding_model_id"] == "voyage:voyage-law-2"


def test_register_duplicate_conflicts(client, seed_user):
    headers = _login(client, seed_user)
    client.post(
        "/v1/embedding-indexes",
        json={"provider": "voyage", "model_id": "voyage-law-2", "dimension": 1024},
        headers=headers,
    )

    resp = client.post(
        "/v1/embedding-indexes",
        json={"provider": "voyage", "model_id": "voyage-law-2", "dimension": 1024},
        headers=headers,
    )
    assert resp.status_code == 409


def test_set_default_rejects_non_ready_index(client, seed_user):
    headers = _login(client, seed_user)
    client.post(
        "/v1/embedding-indexes",
        json={"provider": "voyage", "model_id": "voyage-law-2", "dimension": 1024},
        headers=headers,
    )

    resp = client.patch(
        "/v1/embedding-indexes/voyage:voyage-law-2",
        json={"is_default": True},
        headers=headers,
    )
    assert resp.status_code == 400


def test_set_default_succeeds_for_ready_index(client, seed_user, db_conn):
    headers = _login(client, seed_user)
    db_conn.execute(
        "INSERT INTO embedding_models (embedding_model_id, provider, model_id, dimension, "
        "status, table_name) VALUES (%s, %s, %s, %s, %s, %s)",
        (
            "openai:text-embedding-3-large",
            "openai",
            "text-embedding-3-large",
            3072,
            "ready",
            "clause_embeddings_openai_text_embedding_3_large",
        ),
    )

    resp = client.patch(
        "/v1/embedding-indexes/openai:text-embedding-3-large",
        json={"is_default": True},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_default"] is True


def test_set_default_unknown_index_404(client, seed_user):
    headers = _login(client, seed_user)
    resp = client.patch(
        "/v1/embedding-indexes/openai:does-not-exist",
        json={"is_default": True},
        headers=headers,
    )
    assert resp.status_code == 404


def test_embedding_indexes_require_auth(client):
    resp = client.get("/v1/embedding-indexes")
    assert resp.status_code == 401
