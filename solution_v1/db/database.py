from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from utils.config import DATABASE_URL
from datetime import datetime
import os

db_url = DATABASE_URL
if db_url.startswith("sqlite:///"):
    path = db_url.replace("sqlite:///", "")
    if not os.path.isabs(path):
        db_url = "sqlite:///" + os.path.join(os.path.dirname(os.path.dirname(__file__)), path)

engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    patient_id = Column(String, index=True)
    trial_id = Column(String, index=True)
    criterion_id = Column(String)
    source_id = Column(String)
    rule = Column(String)
    evaluation_result = Column(String)
    decision = Column(String)
    engine_version = Column(String, default="Synapse-KG v0.1")

Base.metadata.create_all(bind=engine)