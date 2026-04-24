from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship

class User(SQLModel, table=True):
    user_id: int = Field(primary_key=True)
    username: Optional[str] = None
    email: Optional[str] = None
    password_hash: Optional[str] = None  # For web authentication
    user_type: str = Field(default="exchange")  # "exchange", "mentor", "learner"
    teach_skill: Optional[str] = None
    learn_skill: Optional[str] = None
    rating: float = Field(default=0.0)
    rating_count: int = Field(default=0)
    matches_count: int = Field(default=0)
    bio: Optional[str] = ""
    experience_level: Optional[str] = ""
    language: str = Field(default="uz")
    is_active: bool = Field(default=True)
    is_pro: bool = Field(default=False)
    is_admin: bool = Field(default=False)
    invited_by: Optional[int] = Field(default=None, foreign_key="user.user_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

class Match(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_a_id: int = Field(foreign_key="user.user_id")
    user_b_id: int = Field(foreign_key="user.user_id")
    is_active: bool = Field(default=True)
    is_followed_up: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class QueueItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.user_id", unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class RatingRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    rater_id: int = Field(foreign_key="user.user_id")
    target_id: int = Field(foreign_key="user.user_id")
    score: int
    comment: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
