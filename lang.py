"""
storage.py — Database-backed data store for SkillBridge.
"""
from typing import Optional, List, Dict, Any
from sqlmodel import Session, select, func, delete
from skillbridge_bot.data.database import engine
from skillbridge_bot.data.models import User, Match, QueueItem, RatingRecord
from skillbridge_bot.utils.helpers import get_current_timestamp

# Helper to get a session (since storage functions are called in a sync manner usually)
# For better performance in a web-app, we would pass sessions, but for this bot MVP
# opening a session per-call is safe for SQLite.

# ---------------------------------------------------------------------------
# Language & Configuration
# ---------------------------------------------------------------------------

def set_user_language(user_id: int, lang_code: str) -> None:
    with Session(engine) as session:
        user = session.get(User, user_id)
        if user:
            user.language = lang_code
            session.add(user)
            session.commit()

def get_user_language(user_id: int) -> Optional[str]:
    with Session(engine) as session:
        user = session.get(User, user_id)
        return user.language if user else None


# ---------------------------------------------------------------------------
# User CRUD helpers
# ---------------------------------------------------------------------------

def create_user(
        user_id: int,
        username: str,
        teach_skill: str,
        learn_skill: str,
        user_type: str = "exchange",
        invited_by: Optional[int] = None,
        email: Optional[str] = None,
        password_hash: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new user. Re-registration overwrites the old record partially."""
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            user = User(user_id=user_id)

        user.username = username or f"user_{user_id}"
        user.teach_skill = teach_skill.strip().lower()
        user.learn_skill = learn_skill.strip().lower()
        user.user_type = user_type
        if invited_by:
            user.invited_by = invited_by
        if email:
            user.email = email
        if password_hash:
            user.password_hash = password_hash

        session.add(user)
        session.commit()
        session.refresh(user)
        return user.model_dump()


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    with Session(engine) as session:
        user = session.get(User, user_id)
        return user.model_dump() if user else None


def get_user_by_username(username: str) -> Optional[User]:
    """Get user by username (returns User object for auth purposes)"""
    with Session(engine) as session:
        statement = select(User).where(User.username == username.lower().strip())
        user = session.exec(statement).first()
        return user  # Return the User object directly for auth


def update_user(user_id: int, **kwargs) -> Optional[Dict[str, Any]]:
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            return None
        
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.model_dump()


def user_exists(user_id: int) -> bool:
    with Session(engine) as session:
        user = session.get(User, user_id)
        return user is not None


def get_all_users() -> List[Dict[str, Any]]:
    with Session(engine) as session:
        statement = select(User)
        results = session.exec(statement).all()
        return [u.model_dump() for u in results]


def get_user_stats() -> Dict[str, int]:
    """Return overall statistics for the admin dashboard."""
    with Session(engine) as session:
        total_users = session.exec(select(func.count(User.user_id))).one()
        total_matches = session.exec(select(func.count(Match.id)).where(Match.is_active == True)).one()
        total_mentors = session.exec(select(func.count(User.user_id)).where(User.user_type == "mentor")).one()
        active_in_queue = session.exec(select(func.count(QueueItem.id))).one()
        
        return {
            "total_users": total_users,
            "active_users": total_users,  
            "total_matches": total_matches,
            "total_mentors": total_mentors,
            "active_in_queue": active_in_queue,
            "total_ratings": session.exec(select(func.count(RatingRecord.id)).where(RatingRecord.score > 0)).one()
        }

# ---------------------------------------------------------------------------
# Waiting queue helpers
# ---------------------------------------------------------------------------
def add_to_queue(user_id: int) -> None:
    with Session(engine) as session:
        # Check if already in queue
        existing = session.exec(select(QueueItem).where(QueueItem.user_id == user_id)).first()
        if not existing:
            item = QueueItem(user_id=user_id)
            session.add(item)
            session.commit()

def remove_from_queue(user_id: int) -> None:
    with Session(engine) as session:
        statement = delete(QueueItem).where(QueueItem.user_id == user_id)
        session.exec(statement)
        session.commit()

def get_queue() -> List[int]:
    with Session(engine) as session:
        statement = select(QueueItem.user_id).order_by(QueueItem.created_at)
        results = session.exec(statement).all()
        return list(results)

# ---------------------------------------------------------------------------
# Match helpers
# ---------------------------------------------------------------------------
def add_match(user_a: int, user_b: int) -> None:
    with Session(engine) as session:
        match = Match(user_a_id=user_a, user_b_id=user_b)
        session.add(match)
        
        # Update user match counts
        for uid in (user_a, user_b):
            user = session.get(User, uid)
            if user:
                user.matches_count += 1
                session.add(user)
        
        session.commit()

def get_match(user_id: int) -> Optional[int]:
    with Session(engine) as session:
        statement = select(Match).where(
            ((Match.user_a_id == user_id) | (Match.user_b_id == user_id)) & (Match.is_active == True)
        )
        match = session.exec(statement).first()
        if match:
            return match.user_b_id if match.user_a_id == user_id else match.user_a_id
        return None

def remove_match(user_id: int) -> None:
    with Session(engine) as session:
        statement = select(Match).where(
            ((Match.user_a_id == user_id) | (Match.user_b_id == user_id)) & (Match.is_active == True)
        )
        match = session.exec(statement).first()
        if match:
            match.is_active = False
            session.add(match)
            session.commit()

def have_matched_before(user_a: int, user_b: int) -> bool:
    """Check if two users have ever been matched together (regardless of status)."""
    with Session(engine) as session:
        statement = select(Match).where(
            ((Match.user_a_id == user_a) & (Match.user_b_id == user_b)) |
            ((Match.user_a_id == user_b) & (Match.user_b_id == user_a))
        )
        match = session.exec(statement).first()
        return match is not None

def get_matches_for_followup(hours_ago: int = 24) -> List[Match]:
    from datetime import datetime, timedelta
    threshold = datetime.utcnow() - timedelta(hours=hours_ago)
    with Session(engine) as session:
        statement = select(Match).where(
            (Match.is_active == True) & 
            (Match.is_followed_up == False) & 
            (Match.created_at <= threshold)
        )
        return list(session.exec(statement).all())

def mark_followed_up(match_id: int) -> None:
    with Session(engine) as session:
        match = session.get(Match, match_id)
        if match:
            match.is_followed_up = True
            session.add(match)
            session.commit()

# ---------------------------------------------------------------------------
# Rating helpers
# ---------------------------------------------------------------------------
def add_rating(rater_id: int, target_user_id: int, score: int, comment: Optional[str] = None) -> None:
    with Session(engine) as session:
        user = session.get(User, target_user_id)
        if not user:
            return
        
        # Update user totals
        count = user.rating_count
        avg   = user.rating
        user.rating       = (avg * count + score) / (count + 1)
        user.rating_count = count + 1
        session.add(user)

        # Create rating record
        record = RatingRecord(rater_id=rater_id, target_id=target_user_id, score=score, comment=comment)
        session.add(record)
        
        session.commit()

def get_testimonials(limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch high-rated testimonials with comments for the website."""
    with Session(engine) as session:
        statement = select(RatingRecord, User.username).join(User, RatingRecord.rater_id == User.user_id).where(
            (RatingRecord.score >= 4) & (RatingRecord.comment != None)
        ).order_by(RatingRecord.created_at.desc()).limit(limit)
        
        results = session.exec(statement).all()
        return [
            {
                "username": row[1],
                "score": row[0].score,
                "comment": row[0].comment,
                "created_at": row[0].created_at.isoformat()
            } for row in results
        ]

def set_pending_rating(rater_id: int, target_id: int) -> None:
    # This is often transient, but let's keep it in DB for persistence across restarts
    with Session(engine) as session:
        # Remove old if exists
        session.exec(delete(RatingRecord).where(RatingRecord.rater_id == rater_id))
        record = RatingRecord(rater_id=rater_id, target_id=target_id, score=0) # placeholder score
        session.add(record)
        session.commit()

def get_pending_rating(rater_id: int) -> Optional[int]:
    with Session(engine) as session:
        statement = select(RatingRecord.target_id).where(RatingRecord.rater_id == rater_id)
        result = session.exec(statement).first()
        return result

def clear_pending_rating(rater_id: int) -> None:
    with Session(engine) as session:
        statement = delete(RatingRecord).where(RatingRecord.rater_id == rater_id)
        session.exec(statement)
        session.commit()

# ---------------------------------------------------------------------------
# Pending Mentor helpers (Re-using User fields is better, but keeping for compatibility)
# ---------------------------------------------------------------------------
# We can use the bio/experience fields in the User model directly.

def add_pending_mentor(user_id: int, bio: str, experience_level: str) -> None:
    # Just update the user record directly
    update_user(user_id, bio=bio, experience_level=experience_level)

def get_pending_mentor(user_id: int) -> Optional[Dict[str, str]]:
    user = get_user(user_id)
    if user and user.get("bio"):
        return {"bio": user["bio"], "experience_level": user["experience_level"]}
    return None

def remove_pending_mentor(user_id: int) -> None:
    # Just reset the fields
    update_user(user_id, bio="", experience_level="")

def get_referral_count(user_id: int) -> int:
    with Session(engine) as session:
        statement = select(func.count(User.user_id)).where(User.invited_by == user_id)
        return session.exec(statement).one()
