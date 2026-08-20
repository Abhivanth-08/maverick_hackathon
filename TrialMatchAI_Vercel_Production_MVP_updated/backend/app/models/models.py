from datetime import datetime, date
from sqlalchemy import String, Text, Date, DateTime, ForeignKey, Integer, Float, Boolean, JSON, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database.session import Base

class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="RESEARCHER")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    external_patient_id: Mapped[str] = mapped_column(String(100), index=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    sex: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("organization_id", "external_patient_id"),)

class PatientCondition(Base):
    __tablename__ = "patient_conditions"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    condition_code: Mapped[str | None] = mapped_column(String(100))
    condition_name: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str | None] = mapped_column(String(50))
    onset_date: Mapped[date | None] = mapped_column(Date)
    resolved_date: Mapped[date | None] = mapped_column(Date)
    source: Mapped[str | None] = mapped_column(String(100))

class PatientMedication(Base):
    __tablename__ = "patient_medications"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    medication_code: Mapped[str | None] = mapped_column(String(100))
    medication_name: Mapped[str] = mapped_column(String(255), index=True)
    dose: Mapped[str | None] = mapped_column(String(100))
    route: Mapped[str | None] = mapped_column(String(100))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str | None] = mapped_column(String(50))
    source: Mapped[str | None] = mapped_column(String(100))

class PatientLab(Base):
    __tablename__ = "patient_labs"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    test_code: Mapped[str | None] = mapped_column(String(100))
    test_name: Mapped[str] = mapped_column(String(255), index=True)
    value_numeric: Mapped[float | None] = mapped_column(Float)
    value_text: Mapped[str | None] = mapped_column(String(255))
    unit: Mapped[str | None] = mapped_column(String(50))
    reference_range: Mapped[str | None] = mapped_column(String(100))
    abnormal_flag: Mapped[str | None] = mapped_column(String(30))
    observed_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    source: Mapped[str | None] = mapped_column(String(100))

class ClinicalEvent(Base):
    __tablename__ = "clinical_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    event_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    source: Mapped[str | None] = mapped_column(String(100))
    source_record_id: Mapped[str | None] = mapped_column(String(150))
    payload: Mapped[dict | None] = mapped_column(JSON)

class PatientNote(Base):
    """Free-text clinical notes. Raw text is never persisted — only the Presidio-
    anonymized text and the detected entity types/spans are stored, so PII never
    lands in the database in the first place."""
    __tablename__ = "patient_notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    anonymized_text: Mapped[str] = mapped_column(Text)
    detected_entities: Mapped[list | None] = mapped_column(JSON)
    anonymization_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    author_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Trial(Base):
    __tablename__ = "trials"
    id: Mapped[int] = mapped_column(primary_key=True)
    nct_id: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    title: Mapped[str] = mapped_column(Text)
    official_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), index=True)
    phase: Mapped[str | None] = mapped_column(String(50))
    conditions: Mapped[list | None] = mapped_column(JSON)
    interventions: Mapped[list | None] = mapped_column(JSON)
    min_age: Mapped[float | None] = mapped_column(Float)
    max_age: Mapped[float | None] = mapped_column(Float)
    sex: Mapped[str | None] = mapped_column(String(30))
    healthy_volunteers: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    study_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    enrollment: Mapped[int | None] = mapped_column(Integer, nullable=True)
    locations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    sponsor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    eligibility_text: Mapped[str | None] = mapped_column(Text)
    last_update_date: Mapped[date | None] = mapped_column(Date)

class TrialCriterion(Base):
    __tablename__ = "trial_criteria"
    id: Mapped[int] = mapped_column(primary_key=True)
    trial_id: Mapped[int] = mapped_column(ForeignKey("trials.id"), index=True)
    criterion_type: Mapped[str] = mapped_column(String(20), index=True)
    criterion_text: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), index=True)
    operator: Mapped[str | None] = mapped_column(String(30))
    structured_value: Mapped[str | None] = mapped_column(String(100))
    unit: Mapped[str | None] = mapped_column(String(30))
    temporal_constraint: Mapped[str | None] = mapped_column(String(100))
    confidence: Mapped[float | None] = mapped_column(Float)
    source_text: Mapped[str | None] = mapped_column(Text)

class MatchResult(Base):
    __tablename__ = "match_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    trial_id: Mapped[int] = mapped_column(ForeignKey("trials.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    evidence_completeness: Mapped[float] = mapped_column(Float, default=0)
    ranking_score: Mapped[float] = mapped_column(Float, default=0)
    met_count: Mapped[int | None] = mapped_column(Integer, default=0)
    not_met_count: Mapped[int | None] = mapped_column(Integer, default=0)
    unknown_count: Mapped[int | None] = mapped_column(Integer, default=0)
    conflicting_count: Mapped[int | None] = mapped_column(Integer, default=0)
    screening_coverage: Mapped[float | None] = mapped_column(Float, default=0)
    explanation: Mapped[str | None] = mapped_column(Text)
    engine_version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MatchCriterionResult(Base):
    __tablename__ = "match_criteria_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("match_results.id"), index=True)
    criterion_id: Mapped[int] = mapped_column(ForeignKey("trial_criteria.id"), index=True)
    decision: Mapped[str] = mapped_column(String(20), index=True)
    reason: Mapped[str] = mapped_column(Text)
    evidence_source: Mapped[str | None] = mapped_column(String(100))
    evidence_record_id: Mapped[str | None] = mapped_column(String(150))
    evidence_date: Mapped[datetime | None] = mapped_column(DateTime)
    confidence: Mapped[float | None] = mapped_column(Float)

class ScreeningJob(Base):
    __tablename__ = "screening_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    trial_id: Mapped[int | None] = mapped_column(ForeignKey("trials.id"), index=True)
    job_type: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default="QUEUED", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="INFO")
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[str | None] = mapped_column(String(100))
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(index=True)
    user_id: Mapped[int | None] = mapped_column(index=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[str | None] = mapped_column(String(100))
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PatientReport(Base):
    __tablename__ = "patient_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(100))
    document_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processing_status: Mapped[str] = mapped_column(String(50), default="UPLOADED", index=True)
    extraction_status: Mapped[str] = mapped_column(String(50), default="PENDING", index=True)
    extracted_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    verified_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

