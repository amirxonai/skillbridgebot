"""
SkillBridge.uz — FastAPI Backend
Runs the web site and exposes REST API endpoints.
"""
import os
import sys
import random
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, status, Request, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
import re

# ------------------------------------------------------------------
# Make sure the project root is importable
# ------------------------------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ------------------------------------------------------------------
# Import site configuration and authentication
# ------------------------------------------------------------------
from skillbridge_site.config import CORS_ORIGINS, ADMIN_API_KEY, DOMAIN, SITE_URL, API_BASE_URL
from skillbridge_site.backend.auth import (
    create_access_token,
    verify_token,
    hash_password,
    verify_password,
    extract_token_from_header,
    TokenData
)



# ------------------------------------------------------------------
# Import bot data layer (graceful fallback if bot is not installed)
# ------------------------------------------------------------------
try:
    from skillbridge_bot.data import storage
    from skillbridge_bot.services import mentor_service

    # We no longer seed demo users. Real results only!

    STORAGE_OK = True
except Exception as e:
    print(f"[WARN] Could not import bot storage: {e}. Using in-memory fallback.")
    STORAGE_OK = False

# ------------------------------------------------------------------
# In-memory fallback when bot storage is unavailable
# ------------------------------------------------------------------
_fallback_users: list = []
_fallback_id_counter = -1000

def _fallback_create(user_id, username, teach, learn, utype):
    _fallback_users.append({
        "user_id": user_id, "username": username,
        "teach_skill": teach, "learn_skill": learn,
        "user_type": utype, "rating": 0.0, "rating_count": 0,
        "bio": "", "experience_level": "",
    })

def _fallback_get_all():
    return _fallback_users

def _fallback_get_mentors(limit=10):
    return [u for u in _fallback_users if u["user_type"] == "mentor"][:limit]

# ------------------------------------------------------------------
# FastAPI App
# ------------------------------------------------------------------
app = FastAPI(
    title="SkillBridge.uz API",
    description="Backend API for SkillBridge — O'zbekiston bilim almashish platformasi",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=True,
)

# ------------------------------------------------------------------
# Pydantic Models
# ------------------------------------------------------------------
class WebRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    teach: str = Field(..., min_length=2, max_length=100)
    learn: str = Field(..., min_length=2, max_length=100)

    @validator('name')
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-Z0-9 \-\.\']+$', v):
            raise ValueError('Name contains invalid characters')
        return v.strip()

    @validator('teach', 'learn')
    def validate_skill(cls, v):
        if not v.strip():
            raise ValueError('Skill cannot be empty')
        return v.strip().lower()

class UserResponse(BaseModel):
    user_id: int
    username: str
    teach_skill: str
    learn_skill: str
    rating: float
    rating_count: int
    user_type: str
    bio: str = ""
    
class TestimonialResponse(BaseModel):
    username: str
    score: int
    comment: str
    created_at: str

# ------------------------------------------------------------------
# API Endpoints
# ------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok", "storage": "bot" if STORAGE_OK else "fallback"}


@app.get("/api/stats")
async def get_stats():
    if STORAGE_OK:
        try:
            return storage.get_user_stats()
        except Exception:
            pass
    users = _fallback_get_all()
    return {
        "total_users": len(users),
        "mentors": sum(1 for u in users if u.get("user_type") == "mentor"),
        "exchanges": sum(1 for u in users if u.get("user_type") == "exchange"),
    }


@app.get("/api/mentors", response_model=List[UserResponse])
async def get_mentors(limit: int = 9):
    if STORAGE_OK:
        try:
            mentors = mentor_service.get_top_mentors(limit=limit)
            return mentors
        except Exception:
            pass
    return _fallback_get_mentors(limit)


@app.get("/api/skills")
async def get_skills():
    if STORAGE_OK:
        try:
            users_list = storage.get_all_users()
            skill_counts: dict = {}
            for u in users_list:
                s = u.get("teach_skill", "").strip().lower()
                if s:
                    skill_counts[s] = skill_counts.get(s, 0) + 1
            return [{"skill": k.title(), "count": v} for k, v in sorted(skill_counts.items(), key=lambda x: -x[1])]
        except Exception:
            pass
    return []


@app.get("/api/testimonials", response_model=List[TestimonialResponse])
async def get_testimonials(limit: int = 5):
    if STORAGE_OK:
        try:
            return storage.get_testimonials(limit=limit)
        except Exception:
            pass
    return []


@app.get("/api/admin/stats")
async def get_admin_stats(request: Request, api_key: str = None):
    """Get admin statistics (protected endpoint)."""
    # Simple API key protection
    if not api_key or api_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )

    if STORAGE_OK:
        try:
            return storage.get_user_stats()
        except Exception:
            pass
    return {"error": "Stats unavailable"}


@app.post("/api/register")
async def register_user(request: Request, reg: WebRegister):
    global _fallback_id_counter
    user_id = -random.randint(10000, 99999)

    if STORAGE_OK:
        try:
            storage.create_user(user_id, reg.name, reg.teach, reg.learn, "exchange")
        except Exception as e:
            print(f"[WARN] storage.create_user failed: {e}")
    else:
        _fallback_create(user_id, reg.name, reg.teach, reg.learn, "exchange")

    # Notify admin via bot (optional — works only when bot is running together)
    try:
        from skillbridge_bot.config import ADMIN_IDS
        bot = getattr(app.state, "bot", None)
        if bot and ADMIN_IDS:
            msg = (
                f"🆕 <b>Yangi Veb-Ro'yxat!</b>\n\n"
                f"👤 Ism: {reg.name}\n"
                f"📚 O'rgatadi: {reg.teach}\n"
                f"🎓 O'rganadi: {reg.learn}"
            )
            for admin_id in ADMIN_IDS:
                try:
                    await bot.send_message(admin_id, msg, parse_mode="HTML")
                except Exception as e:
                    print(f"[WARN] Admin notify failed ({admin_id}): {e}")
    except Exception:
        pass  # Bot not running — that's fine

    return {"status": "success", "user_id": user_id, "message": "Muvaffaqiyatli ro'yxatdan o'tdingiz!"}


# ------------------------------------------------------------------
# Authentication Endpoints
# ------------------------------------------------------------------

class LoginRequest(BaseModel):
    """User login request"""
    username: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)

class RegisterAuthRequest(BaseModel):
    """User registration with password"""
    username: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)
    teach: str = Field(..., min_length=2, max_length=100)
    learn: str = Field(..., min_length=2, max_length=100)

    @validator('username')
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_\-]+$', v):
            raise ValueError('Username contains invalid characters')
        return v.lower().strip()

    @validator('email')
    def validate_email(cls, v):
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Invalid email format')
        return v.lower().strip()

@app.post("/api/auth/register")
async def register_with_password(req: RegisterAuthRequest):
    """Register user with email and password"""
    if STORAGE_OK:
        try:
            # Check if username already exists
            existing = storage.get_user_by_username(req.username)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )

            # Create user with password
            user_id = storage.create_user(
                -random.randint(10000, 99999),
                req.username,
                req.teach,
                req.learn,
                "exchange",
                email=req.email,
                password_hash=hash_password(req.password)
            )

            # Create token
            token = create_access_token(user_id, req.username)

            return {
                "status": "success",
                "user_id": user_id,
                "access_token": token.access_token,
                "token_type": token.token_type
            }
        except HTTPException:
            raise
        except Exception as e:
            print(f"[WARN] Auth register failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Registration failed"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage not available"
        )

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    """User login with username and password"""
    if STORAGE_OK:
        try:
            # Get user by username
            user = storage.get_user_by_username(req.username)
            if not user or not user.password_hash:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password"
                )

            # Verify password
            if not verify_password(req.password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password"
                )

            # Update last login
            storage.update_user(user.user_id, last_login=datetime.utcnow())

            # Create token
            token = create_access_token(user.user_id, user.username)

            return {
                "status": "success",
                "user_id": user.user_id,
                "username": user.username,
                "access_token": token.access_token,
                "token_type": token.token_type
            }
        except HTTPException:
            raise
        except Exception as e:
            print(f"[WARN] Auth login failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Login failed"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage not available"
        )

@app.get("/api/auth/verify")
async def verify_auth(authorization: Optional[str] = Header(None)):
    """Verify JWT token"""
    token = extract_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid token"
        )

    token_data = verify_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    return {
        "status": "valid",
        "user_id": token_data.user_id,
        "username": token_data.username
    }

async def get_current_user(authorization: Optional[str] = Header(None)) -> TokenData:
    """Dependency to get current authenticated user"""
    token = extract_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token"
        )

    token_data = verify_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    return token_data

@app.get("/api/auth/me")
async def get_current_user_info(current_user: TokenData = Depends(get_current_user)):
    """Get current authenticated user info"""
    if STORAGE_OK:
        try:
            user = storage.get_user(current_user.user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            return {
                "user_id": user.user_id,
                "username": user.username,
                "teach_skill": user.teach_skill,
                "learn_skill": user.learn_skill,
                "user_type": user.user_type,
                "rating": user.rating,
                "is_pro": user.is_pro
            }
        except HTTPException:
            raise
        except Exception as e:
            print(f"[WARN] Get user info failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get user info"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage not available"
        )

FRONTEND = os.path.join(os.path.dirname(__file__), "../frontend")
if os.path.isdir(FRONTEND):
    app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="static")

# ------------------------------------------------------------------
# Run directly
# ------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 80))
    print(f"\n🚀 SkillBridge.uz   →   http://skillbridge.uz\n")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
