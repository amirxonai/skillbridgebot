import os
from sqlmodel import SQLModel, create_engine, Session, select
from typing import Generator
from skillbridge_bot.config import DATABASE_URL

# Engine creation
# For SQLite we need check_same_thread=False
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)

def init_db():
    print(f"Initializing database: {DATABASE_URL}")
    SQLModel.metadata.create_all(engine)
    _create_indexes()

def _create_indexes():
    """Create strategic indexes for performance optimization."""
    with Session(engine) as session:
        # List of indexes to create (SQLite compatible)
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_user_user_type ON user(user_type)",
            "CREATE INDEX IF NOT EXISTS idx_user_created_at ON user(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_queue_user_id ON queueitem(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_match_user_a ON match(user_a_id)",
            "CREATE INDEX IF NOT EXISTS idx_match_user_b ON match(user_b_id)",
            "CREATE INDEX IF NOT EXISTS idx_match_is_active ON match(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_rating_target ON ratingrecord(target_id)",
            "CREATE INDEX IF NOT EXISTS idx_rating_rater ON ratingrecord(rater_id)",
        ]

        for index_sql in indexes:
            try:
                session.exec(index_sql)
                session.commit()
                print(f"✓ {index_sql.split('ON')[1].strip()}")
            except Exception as e:
                # Index might already exist
                pass

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
