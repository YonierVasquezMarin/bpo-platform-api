import pytest
from cryptography.exceptions import InvalidTag

from app.core.crypto import PasswordCipher


def test_encrypt_and_decrypt_password_roundtrip() -> None:
    cipher = PasswordCipher(
        encryption_key="clave-de-prueba",
        encryption_salt="sal-de-prueba",
    )
    password = "Admin1234#ABC"

    encrypted_password = cipher.encrypt_password(password)
    decrypted_password = cipher.decrypt_password(encrypted_password)

    assert encrypted_password != password
    assert decrypted_password == password


def test_decrypt_fails_with_different_keys() -> None:
    original_cipher = PasswordCipher(
        encryption_key="clave-original",
        encryption_salt="sal-original",
    )
    other_cipher = PasswordCipher(
        encryption_key="clave-distinta",
        encryption_salt="sal-distinta",
    )
    encrypted_password = original_cipher.encrypt_password("secreto")

    with pytest.raises(InvalidTag):
        other_cipher.decrypt_password(encrypted_password)


def test_missing_keys_raise_value_error() -> None:
    with pytest.raises(ValueError, match="ENCRYPTION_KEY y ENCRYPTION_SALT"):
        PasswordCipher(encryption_key="   ", encryption_salt="sal")
