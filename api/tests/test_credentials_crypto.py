from app.credentials import decrypt_key, encrypt_key, key_suffix


def test_encrypt_decrypt_round_trip():
    plaintext = "sk-ant-abcdef1234567890"
    ciphertext = encrypt_key(plaintext)
    assert ciphertext != plaintext.encode()
    assert decrypt_key(ciphertext) == plaintext


def test_key_suffix():
    assert key_suffix("sk-ant-abcdef1234567890") == "7890"


def test_key_suffix_short_key():
    assert key_suffix("ab") == "ab"
