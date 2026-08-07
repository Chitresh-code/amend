from app.auth.sessions import hash_session_token


def test_hash_session_token_deterministic():
    token = "some-raw-session-token"
    assert hash_session_token(token) == hash_session_token(token)


def test_hash_session_token_differs_by_input():
    assert hash_session_token("token-a") != hash_session_token("token-b")


def test_hash_session_token_not_the_raw_token():
    token = "some-raw-session-token"
    assert hash_session_token(token) != token
