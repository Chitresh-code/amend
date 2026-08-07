from app.auth.passwords import hash_password, verify_password


def test_verify_correct_password():
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password(hashed, "correct-horse-battery-staple") is True


def test_verify_wrong_password():
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password(hashed, "wrong-password") is False


def test_hash_is_not_plaintext():
    hashed = hash_password("correct-horse-battery-staple")
    assert "correct-horse-battery-staple" not in hashed
