from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from backend.app.core.config import get_settings
import os
import shutil

settings = get_settings()

db_url = settings.database_url
if db_url.startswith("sqlite") and os.getenv("VERCEL"):
    # On Vercel, the filesystem is read-only except for /tmp
    # Copy the DB to /tmp so SQLite can create lock files and write
    db_path = db_url.replace("sqlite:///", "")
    tmp_db_path = "/tmp/trialmatchai.db"
    if os.path.exists(db_path) and not os.path.exists(tmp_db_path):
        shutil.copy2(db_path, tmp_db_path)
    db_url = f"sqlite:///{tmp_db_path}"

connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
engine = create_engine(db_url, pool_pre_ping=True, pool_recycle=300, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
