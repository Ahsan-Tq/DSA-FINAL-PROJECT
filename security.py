import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Optional, Dict, Any


_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_SECRET_PATH = os.path.join(_BASE_DIR, "auth_secret.key")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + pad).encode("ascii"))


def _load_or_create_secret() -> bytes:
    if os.path.exists(_SECRET_PATH):
        with open(_SECRET_PATH, "rb") as f:
            secret = f.read()
        if len(secret) >= 32:
            return secret
    secret = secrets.token_bytes(32)
    with open(_SECRET_PATH, "wb") as f:
        f.write(secret)
    return secret


def hash_password(password: str, iterations: int = 200_000) -> str:
    if password is None:
        password = ""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=32)
    return "pbkdf2_sha256$%d$%s$%s" % (
        iterations,
        _b64url_encode(salt),
        _b64url_encode(dk),
    )


def verify_password(password: str, stored: str) -> bool:
    if password is None:
        password = ""
    try:
        scheme, iters_s, salt_s, hash_s = stored.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        iterations = int(iters_s)
        salt = _b64url_decode(salt_s)
        expected = _b64url_decode(hash_s)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=len(expected))
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


def issue_token(user_id: int, username: str, role: str, ttl_seconds: int = 8 * 60 * 60) -> str:
    secret = _load_or_create_secret()
    now = int(time.time())
    header = {"alg": "HS256", "typ": "BJWT"}
    payload = {
        "uid": int(user_id),
        "usr": str(username),
        "role": str(role),
        "iat": now,
        "exp": now + int(ttl_seconds),
        "nonce": secrets.token_urlsafe(12),
    }
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signing_input = (header_b64 + "." + payload_b64).encode("ascii")
    sig = hmac.new(secret, signing_input, hashlib.sha256).digest()
    return header_b64 + "." + payload_b64 + "." + _b64url_encode(sig)


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        secret = _load_or_create_secret()
        header_b64, payload_b64, sig_b64 = token.split(".", 2)
        signing_input = (header_b64 + "." + payload_b64).encode("ascii")
        sig = _b64url_decode(sig_b64)
        expected = hmac.new(secret, signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None

