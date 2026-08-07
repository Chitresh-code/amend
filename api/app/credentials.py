from cryptography.fernet import Fernet

from app.config import settings

_fernet = Fernet(settings.credential_encryption_key.encode())


def encrypt_key(plaintext_key: str) -> bytes:
    return _fernet.encrypt(plaintext_key.encode())


def decrypt_key(ciphertext: bytes) -> str:
    return _fernet.decrypt(ciphertext).decode()


def key_suffix(plaintext_key: str, length: int = 4) -> str:
    return plaintext_key[-length:] if len(plaintext_key) >= length else plaintext_key
