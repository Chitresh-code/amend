from app.auth.csrf import csrf_token_valid, generate_csrf_token


def test_matching_tokens_valid():
    token = generate_csrf_token()
    assert csrf_token_valid(token, token) is True


def test_mismatched_tokens_invalid():
    assert csrf_token_valid(generate_csrf_token(), generate_csrf_token()) is False


def test_missing_tokens_invalid():
    assert csrf_token_valid(None, "x") is False
    assert csrf_token_valid("x", None) is False
    assert csrf_token_valid(None, None) is False
