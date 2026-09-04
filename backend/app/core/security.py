import os
import base64
import json
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

# Secret key for JWT signing (uses environment variable if configured, else default secure fallback)
SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "ner-landslide-surveillance-secure-key-2026-auth")
TOKEN_EXPIRE_HOURS = 24 * 7  # 7 days session validity

def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def _base64url_decode(data: str) -> bytes:
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + padding)

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with a random salt."""
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"pbkdf2_sha256${salt.hex()}${key.hex()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against stored hash."""
    if not hashed_password:
        return False
    # Check if format matches pbkdf2_sha256$salt$hash
    if hashed_password.startswith("pbkdf2_sha256$"):
        parts = hashed_password.split("$")
        if len(parts) == 3:
            salt_hex, expected_hex = parts[1], parts[2]
            try:
                salt = bytes.fromhex(salt_hex)
                computed = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100000)
                return secrets.compare_digest(computed.hex(), expected_hex)
            except Exception:
                return False
    # Fallback to direct comparison (for demo/development convenience)
    return secrets.compare_digest(plain_password, hashed_password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generate HS256-signed JWT token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": int(expire.timestamp())})

    header = {"alg": "HS256", "typ": "JWT"}
    header_json = json.dumps(header, separators=(",", ":")).encode("utf-8")
    payload_json = json.dumps(to_encode, separators=(",", ":")).encode("utf-8")

    header_b64 = _base64url_encode(header_json)
    payload_b64 = _base64url_encode(payload_json)

    message = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(SECRET_KEY.encode("utf-8"), message, hashlib.sha256).digest()
    signature_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode HS256 JWT token. Returns payload dict or None."""
    if not token or "." not in token:
        return None
    try:
        parts = token.strip().split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature_b64 = parts

        message = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), message, hashlib.sha256).digest()
        provided_sig = _base64url_decode(signature_b64)

        if not secrets.compare_digest(expected_sig, provided_sig):
            return None

        payload_bytes = _base64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Verify expiration
        exp = payload.get("exp")
        if exp and datetime.now(timezone.utc).timestamp() > exp:
            return None

        return payload
    except Exception:
        return None
