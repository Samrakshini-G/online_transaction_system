"""
Cryptographic utilities: AES-256-GCM for reversible data, SHA-256 for hashing.
"""

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from config import AES_SECRET_KEY, PASSWORD_SALT


def _get_aes_key() -> bytes:
    key = AES_SECRET_KEY.encode("utf-8")
    if len(key) != 32:
        key = hashlib.sha256(key).digest()
    return key


def encrypt_data(plaintext: str) -> str:
    """Encrypt sensitive reversible data using AES-256-GCM."""
    if plaintext is None:
        return ""
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_data(token: str) -> str:
    """Decrypt AES-256-GCM encrypted data."""
    if not token:
        return ""
    raw = base64.b64decode(token.encode("utf-8"))
    nonce, ciphertext = raw[:12], raw[12:]
    key = _get_aes_key()
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


def hash_password(password: str) -> str:
    """Hash password using SHA-256 with application salt."""
    payload = f"{PASSWORD_SALT}{password}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    return hash_password(password) == stored_hash


def hash_for_lookup(value: str) -> str:
    """Create SHA-256 hash for duplicate detection (PAN, Aadhaar)."""
    normalized = value.strip().upper()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
