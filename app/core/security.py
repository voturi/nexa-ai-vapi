"""Security utilities for encryption, authentication, and webhook verification."""
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional

from cryptography.fernet import Fernet
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# API key security
security = HTTPBearer()


class CredentialsManager:
    """Secure credential storage and retrieval."""

    def __init__(self):
        """Initialize with encryption key."""
        self.cipher = Fernet(settings.ENCRYPTION_KEY.encode())

    def encrypt(self, data: dict) -> bytes:
        """Encrypt credentials."""
        json_data = json.dumps(data)
        return self.cipher.encrypt(json_data.encode())

    def decrypt(self, encrypted_data: bytes) -> dict:
        """Decrypt credentials."""
        decrypted = self.cipher.decrypt(encrypted_data)
        return json.loads(decrypted.decode())


credentials_manager = CredentialsManager()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def verify_webhook_signature(
    signature: str,
    body: bytes,
    secret: str,
) -> bool:
    """Verify webhook signature from VAPI."""
    expected = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(signature, expected)


async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Verify tenant API key and return tenant."""
    from app.services.tenant_service import TenantService

    api_key = credentials.credentials

    tenant = await TenantService.get_by_api_key(api_key)

    if not tenant:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )

    return tenant
