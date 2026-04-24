"""
SkillBridge.uz — Authentication & JWT
Handles user authentication, password hashing, and JWT token management
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# =====================================================================
# Models
# =====================================================================

class TokenData(BaseModel):
    """Token payload data"""
    user_id: int
    username: str
    exp: datetime = None

class Token(BaseModel):
    """Token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds

class TokenRefresh(BaseModel):
    """Token refresh request"""
    refresh_token: str

# =====================================================================
# Password Management
# =====================================================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

# =====================================================================
# JWT Token Management
# =====================================================================

def create_access_token(user_id: int, username: str, expires_delta: Optional[timedelta] = None) -> Token:
    """
    Create a JWT access token

    Args:
        user_id: User ID
        username: Username
        expires_delta: Token expiration time delta (default: 24 hours)

    Returns:
        Token object with access_token and expiration info
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

    expire = datetime.now(timezone.utc) + expires_delta

    to_encode = {
        "user_id": user_id,
        "username": username,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    }

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return Token(
        access_token=encoded_jwt,
        expires_in=int(expires_delta.total_seconds())
    )

def verify_token(token: str) -> Optional[TokenData]:
    """
    Verify and decode a JWT token

    Args:
        token: JWT token string

    Returns:
        TokenData if valid, None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        username: str = payload.get("username")
        token_type: str = payload.get("type")

        if user_id is None or username is None or token_type != "access":
            return None

        return TokenData(user_id=user_id, username=username)
    except JWTError:
        return None

def extract_token_from_header(auth_header: Optional[str]) -> Optional[str]:
    """
    Extract token from Authorization header

    Expected format: "Bearer <token>"
    """
    if not auth_header:
        return None

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    return parts[1]
