import base64
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import settings

_NONCE_SIZE_IN_BYTES = 12
_DERIVED_KEY_SIZE_IN_BYTES = 32
_HKDF_INFO = b"bpo-platform-password-encryption"


class PasswordCipher:
    def __init__(self, encryption_key: str, encryption_salt: str) -> None:
        self._encryption_key = encryption_key
        self._encryption_salt = encryption_salt
        self._validate_keys()
        self._aesgcm = self._build_aesgcm()

    def encrypt_password(self, password: str) -> str:
        nonce = self._generate_nonce()
        encrypted_bytes = self._encrypt_bytes(nonce, password)
        return self._encode_payload(nonce, encrypted_bytes)

    def decrypt_password(self, encrypted_password: str) -> str:
        nonce, encrypted_bytes = self._decode_payload(encrypted_password)
        decrypted_bytes = self._decrypt_bytes(nonce, encrypted_bytes)
        return decrypted_bytes.decode("utf-8")

    def _validate_keys(self) -> None:
        if self._keys_are_missing():
            raise ValueError("ENCRYPTION_KEY y ENCRYPTION_SALT deben estar definidas en .env")

    def _keys_are_missing(self) -> bool:
        encryption_key_is_missing = not self._encryption_key.strip()
        encryption_salt_is_missing = not self._encryption_salt.strip()
        return encryption_key_is_missing or encryption_salt_is_missing

    def _build_aesgcm(self) -> AESGCM:
        derived_key = self._derive_key()
        return AESGCM(derived_key)

    def _derive_key(self) -> bytes:
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=_DERIVED_KEY_SIZE_IN_BYTES,
            salt=self._encryption_salt.encode("utf-8"),
            info=_HKDF_INFO,
        )
        return hkdf.derive(self._encryption_key.encode("utf-8"))

    def _generate_nonce(self) -> bytes:
        return os.urandom(_NONCE_SIZE_IN_BYTES)

    def _encrypt_bytes(self, nonce: bytes, password: str) -> bytes:
        return self._aesgcm.encrypt(nonce, password.encode("utf-8"), None)

    def _decrypt_bytes(self, nonce: bytes, encrypted_bytes: bytes) -> bytes:
        return self._aesgcm.decrypt(nonce, encrypted_bytes, None)

    def _encode_payload(self, nonce: bytes, encrypted_bytes: bytes) -> str:
        return base64.urlsafe_b64encode(nonce + encrypted_bytes).decode("utf-8")

    def _decode_payload(self, encrypted_password: str) -> tuple[bytes, bytes]:
        payload = base64.urlsafe_b64decode(encrypted_password.encode("utf-8"))
        payload_is_too_short = len(payload) <= _NONCE_SIZE_IN_BYTES
        if payload_is_too_short:
            raise ValueError("El texto cifrado no tiene un formato válido")
        nonce = payload[:_NONCE_SIZE_IN_BYTES]
        encrypted_bytes = payload[_NONCE_SIZE_IN_BYTES:]
        return nonce, encrypted_bytes


def build_password_cipher_from_settings() -> PasswordCipher:
    return PasswordCipher(
        encryption_key=settings.encryption_key,
        encryption_salt=settings.encryption_salt,
    )
