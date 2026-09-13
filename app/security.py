import base64
import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _get_encryption_key() -> bytes:
    secret = os.getenv("APP_ENCRYPTION_KEY")
    if not secret:
        raise RuntimeError("APP_ENCRYPTION_KEY is missing from the environment.")

    key = base64.b64decode(secret)
    if len(key) != 32:
        raise ValueError("APP_ENCRYPTION_KEY must decode to a 32-byte key.")
    return key


def encrypt_text(value: str) -> dict:
    payload = (value or "").encode("utf-8")
    nonce = os.urandom(12)
    ciphertext = AESGCM(_get_encryption_key()).encrypt(nonce, payload, None)
    return {
        "nonce": base64.b64encode(nonce).decode("utf-8"),
        "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
    }


def decrypt_text(payload):
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload
    if not isinstance(payload, dict) or "nonce" not in payload or "ciphertext" not in payload:
        return payload

    nonce = base64.b64decode(payload["nonce"])
    ciphertext = base64.b64decode(payload["ciphertext"])
    plaintext = AESGCM(_get_encryption_key()).decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")


def encrypt_json(value):
    return encrypt_text(json.dumps(value, ensure_ascii=False))


def decrypt_json(payload):
    text = decrypt_text(payload)
    if text == "":
        return []
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return []


def encrypt_bytes(value: bytes) -> dict:
    nonce = os.urandom(12)
    ciphertext = AESGCM(_get_encryption_key()).encrypt(nonce, value, None)
    return {
        "nonce": base64.b64encode(nonce).decode("utf-8"),
        "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
    }


def decrypt_bytes(payload):
    if payload is None:
        return b""
    if isinstance(payload, (bytes, bytearray)):
        return bytes(payload)
    if not isinstance(payload, dict) or "nonce" not in payload or "ciphertext" not in payload:
        return payload

    nonce = base64.b64decode(payload["nonce"])
    ciphertext = base64.b64decode(payload["ciphertext"])
    return AESGCM(_get_encryption_key()).decrypt(nonce, ciphertext, None)
