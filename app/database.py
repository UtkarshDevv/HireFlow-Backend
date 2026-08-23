from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import get_settings

settings = get_settings()

# SQLite: check_same_thread=False required for multi-threaded FastAPI
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Called at startup."""
    from app.models import user, profile, job, resume, application, cloudprep, course  # noqa: F401 — registers models
    Base.metadata.create_all(bind=engine)
    # Safe column migrations for existing SQLite databases
    with engine.connect() as conn:
        from sqlalchemy import text
        migrations = [
            "ALTER TABLE jobs ADD COLUMN projects JSON DEFAULT '[]'",
            "ALTER TABLE cloudprep_course_days ADD COLUMN youtube_url VARCHAR",
            "ALTER TABLE profiles ADD COLUMN user_id VARCHAR(36)",
            "ALTER TABLE jobs ADD COLUMN user_id VARCHAR(36)",
            "ALTER TABLE resumes ADD COLUMN user_id VARCHAR(36)",
            "ALTER TABLE applications ADD COLUMN user_id VARCHAR(36)",
            "ALTER TABLE cloudprep_course_days ADD COLUMN user_id VARCHAR(36)",
            "ALTER TABLE cloudprep_topics ADD COLUMN user_id VARCHAR(36)",
            "ALTER TABLE cloudprep_sessions ADD COLUMN user_id VARCHAR(36)",
            "ALTER TABLE cloudprep_daily_goals ADD COLUMN user_id VARCHAR(36)",
            "ALTER TABLE cloudprep_notes ADD COLUMN user_id VARCHAR(36)",
            "ALTER TABLE cloudprep_bookmarks ADD COLUMN user_id VARCHAR(36)",
            "ALTER TABLE cloudprep_ai_chats ADD COLUMN user_id VARCHAR(36)",
            "ALTER TABLE cloudprep_interview_attempts ADD COLUMN user_id VARCHAR(36)",
            "ALTER TABLE cloudprep_achievements ADD COLUMN user_id VARCHAR(36)",
            "ALTER TABLE cloudprep_certifications ADD COLUMN user_id VARCHAR(36)",
        ]
        for mig in migrations:
            try:
                conn.execute(text(mig))
                conn.commit()
            except Exception:
                pass
