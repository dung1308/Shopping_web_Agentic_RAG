"""
backend/auth/security.py — Password hashing & JWT token management.
"""

import time
import os
import hmac
import hashlib
import json
import base64
from datetime import datetime, timedelta
from typing import Any, Optional
from backend.config import get_settings

settings = get_settings()

# Try importing passlib / jwt; provide resilient built-in fallbacks if optional dependencies are missing
try:
    from passlib.context import CryptContext
    _pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except Exception:
    _pwd_context = None

try:
    import jwt as pyjwt
except Exception:
    pyjwt = None


def hash_password(password: str) -> str:
    """Hash plain text password."""
    if _pwd_context:
        try:
            return _pwd_context.hash(password)
        except Exception:
            pass
    # Fallback: PBKDF2 SHA256
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return "pbkdf2$" + base64.b64encode(salt).decode("ascii") + "$" + base64.b64encode(key).decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain text password against stored hash."""
    if not hashed_password:
        return False
    if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
        if _pwd_context:
            try:
                return _pwd_context.verify(plain_password, hashed_password)
            except Exception:
                pass
    if hashed_password.startswith("pbkdf2$"):
        parts = hashed_password.split("$")
        if len(parts) == 3:
            salt = base64.b64decode(parts[1].encode("ascii"))
            expected_key = base64.b64decode(parts[2].encode("ascii"))
            computed_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100000)
            return hmac.compare_digest(expected_key, computed_key)
    # Simple fallback check
    if _pwd_context:
        try:
            return _pwd_context.verify(plain_password, hashed_password)
        except Exception:
            pass
    return False


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def _base64url_decode(data_str: str) -> bytes:
    padding = 4 - (len(data_str) % 4)
    if padding != 4:
        data_str += "=" * padding
    return base64.urlsafe_b64encode(data_str.encode("ascii"))


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    now_ts = int(time.time())
    expire_seconds = int(expires_delta.total_seconds()) if expires_delta else (settings.admin_jwt_expire_minutes * 60)
    to_encode.update({"exp": now_ts + expire_seconds, "iat": now_ts})

    if pyjwt:
        try:
            return pyjwt.encode(to_encode, settings.api_secret_key, algorithm=settings.admin_jwt_algorithm)
        except Exception:
            pass

    # Built-in lightweight JWT implementation (HMAC-SHA256)
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(to_encode, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(settings.api_secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _base64url_encode(signature)
    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a signed JWT token."""
    if pyjwt:
        try:
            return pyjwt.decode(token, settings.api_secret_key, algorithms=[settings.admin_jwt_algorithm])
        except Exception:
            pass

    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token format")

    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(settings.api_secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_sig = _base64url_decode(sig_b64)

    # Note: compare digest safely
    if not hmac.compare_digest(_base64url_encode(expected_sig), sig_b64):
        raise ValueError("Invalid token signature")

    payload_json = base64.urlsafe_b64decode(payload_b64 + "==" * (len(payload_b64) % 2)).decode("utf-8")
    payload = json.loads(payload_json)

    exp = payload.get("exp")
    if exp and time.time() > exp:
        raise ValueError("Token expired")

    return payload
