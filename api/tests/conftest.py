import os

os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "55432")
os.environ.setdefault("POSTGRES_DB", "amend_test")
os.environ.setdefault("POSTGRES_USER", "amend")
os.environ.setdefault("POSTGRES_PASSWORD", "amend_test_pw")
os.environ.setdefault("REDIS_URL", "redis://localhost:56379/0")
os.environ.setdefault("NEO4J_USER", "test")
os.environ.setdefault("NEO4J_PASSWORD", "test")
os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", "vv6HWttTtvs2bfSm_H_Gzh1ACRme1jRUr-wtUldclSs=")
os.environ.setdefault("API_KEY_HASH_PEPPER", "test-api-key-pepper")
os.environ.setdefault("SESSION_TOKEN_PEPPER", "test-session-pepper")

import psycopg
import pytest
import redis as sync_redis
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture
def db_conn():
    with psycopg.connect(settings.postgres_dsn, autocommit=True) as conn:
        yield conn


@pytest.fixture(autouse=True)
def clean_state(db_conn):
    db_conn.execute(
        "TRUNCATE TABLE conversations, model_credentials, api_keys, user_sessions, users, "
        "embedding_models RESTART IDENTITY CASCADE"
    )
    sync_redis.from_url(settings.redis_url).flushdb()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def seed_user(db_conn):
    from app.auth.passwords import hash_password

    def _seed(email: str = "analyst@example.com", password: str = "correct-horse-battery") -> str:
        row = db_conn.execute(
            "INSERT INTO users (email, password_hash, organization) VALUES (%s, %s, %s) "
            "RETURNING id",
            (email, hash_password(password), "Example Bank"),
        ).fetchone()
        assert row is not None
        return str(row[0])

    return _seed


@pytest.fixture
def seed_api_key(db_conn):
    from app.auth.api_keys import hash_api_key

    def _seed(user_id: str, label: str = "Production", raw_key: str = "sk-amd-test1234") -> str:
        row = db_conn.execute(
            "INSERT INTO api_keys (user_id, key_hash, key_suffix, label) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (user_id, hash_api_key(raw_key), raw_key[-4:], label),
        ).fetchone()
        assert row is not None
        return str(row[0])

    return _seed


@pytest.fixture
def seed_conversation(db_conn):
    def _seed(user_id: str, title: str = "Test conversation", pinned: bool = False) -> str:
        row = db_conn.execute(
            "INSERT INTO conversations (user_id, title, pinned) VALUES (%s, %s, %s) "
            "RETURNING conversation_id",
            (user_id, title, pinned),
        ).fetchone()
        assert row is not None
        return str(row[0])

    return _seed
