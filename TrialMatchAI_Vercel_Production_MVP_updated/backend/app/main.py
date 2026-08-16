from fastapi import FastAPI, Depends, HTTPException, Header, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.app.core.config import get_settings
from backend.app.core.security import verify_password, create_access_token, hash_password
from backend.app.core.deps import get_current_user
from backend.app.database.session import get_db, Base, engine
from backend.app.models import User, Organization, Patient, PatientCondition, PatientMedication, Trial, MatchResult, MatchCriterionResult, PatientLab, ClinicalEvent, AuditLog, ScreeningJob, Notification, PatientNote, PatientReport
from backend.app.schemas.auth import LoginRequest, TokenResponse
from backend.app.schemas.clinical_extraction import PatientClinicalExtraction
from backend.app.services.dashboard import overview
from backend.app.services.semantic_retrieval import candidate_trials
from backend.app.matching.engine import MatchingEngine
from backend.app.monitoring.change_impact import ChangeImpactService
from backend.app.privacy.presidio_service import PresidioService
from backend.app.services.report_processor import ReportProcessorService
from backend.app.services.clinical_extractor import ClinicalExtractorService
from backend.app.workers.queue import process_one
from datetime import datetime

app=FastAPI(title="TrialMatchAI API", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
s = get_settings()
origins = [x.strip() for x in s.cors_origins.split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
import logging

logger = logging.getLogger("trialmatch.startup")

@app.on_event("startup")
def validate_startup_dependencies():
    logger.info("Validating startup dependencies...")
    presidio = PresidioService.get_instance()
    is_avail, init_err = presidio.is_available()
    if is_avail:
        logger.info("Presidio & spaCy ('en_core_web_sm') validation SUCCESSFUL.")
    else:
        logger.warning(f"Missing spaCy model: en_core_web_sm - {init_err}")
        logger.warning("Install it with: python -m spacy download en_core_web_sm")

@app.get("/api/health")
@app.get("/health")
def health():
    presidio = PresidioService.get_instance()
    is_avail, err = presidio.is_available()
    return {
        "status": "healthy" if is_avail else "degraded",
        "api": "healthy",
        "database": "healthy",
        "presidio": "healthy" if is_avail else "unavailable",
        "spacy_model": "en_core_web_sm" if is_avail else "missing",
        "presidio_error": err if not is_avail else None,
        "service": "trialmatchai"
    }

@app.post("/api/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session=Depends(get_db)):
    user=db.query(User).filter(User.email==body.email).one_or_none()
    if not user or not verify_password(body.password,user.password_hash): raise HTTPException(401,"Invalid credentials")
    return {"access_token":create_access_token(str(user.id)),"token_type":"bearer"}

@app.get("/api/me")
def me(user: User=Depends(get_current_user)): return {"id":user.id,"email":user.email,"role":user.role,"organization_id":user.organization_id}

@app.get("/api/patients")
def patients(limit: int = 50, cursor: int = 0, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    limit = min(max(limit, 1), 100)
    rows = db.query(Patient).filter(Patient.organization_id == user.organization_id, Patient.id > cursor).order_by(Patient.id.desc()).limit(limit + 1).all()
    more = len(rows) > limit
    rows = rows[:limit]
    
    items = []
    for p in rows:
        cond = db.query(PatientCondition).filter(PatientCondition.patient_id == p.id).first()
        reports = db.query(PatientReport).filter(PatientReport.patient_id == p.id).all()
        matches = db.query(MatchResult).filter(MatchResult.patient_id == p.id).all()
        latest_report = reports[-1] if reports else None
        
        items.append({
            "id": p.id,
            "external_patient_id": p.external_patient_id,
            "sex": p.sex,
            "date_of_birth": p.date_of_birth.isoformat() if p.date_of_birth else None,
            "primary_diagnosis": cond.condition_name if cond else "Pending Report",
            "report_status": latest_report.processing_status if latest_report else "No Report",
            "reports_count": len(reports),
            "matches_count": len(matches),
            "updated_at": p.updated_at.isoformat() if p.updated_at else p.created_at.isoformat()
        })
    return {"items": items, "next_cursor": rows[-1].id if more and rows else None, "has_more": more}

@app.get("/api/patients/{patient_id}")
def patient(patient_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(Patient).filter(Patient.id == patient_id, Patient.organization_id == user.organization_id).one_or_none()
    if not p: raise HTTPException(404, "Patient not found")
    
    conditions = db.query(PatientCondition).filter(PatientCondition.patient_id == p.id).all()
    medications = db.query(PatientMedication).filter(PatientMedication.patient_id == p.id).all()
    labs = db.query(PatientLab).filter(PatientLab.patient_id == p.id).order_by(PatientLab.observed_at.desc()).limit(20).all()
    events = db.query(ClinicalEvent).filter(ClinicalEvent.patient_id == p.id).all()
    reports = db.query(PatientReport).filter(PatientReport.patient_id == p.id).all()
    matches = db.query(MatchResult).filter(MatchResult.patient_id == p.id).all()
    
    return {
        "id": p.id,
        "external_patient_id": p.external_patient_id,
        "sex": p.sex,
        "date_of_birth": p.date_of_birth.isoformat() if p.date_of_birth else None,
        "status": p.status,
        "conditions": [{"id": c.id, "name": c.condition_name, "status": c.status} for c in conditions],
        "medications": [{"id": m.id, "name": m.medication_name, "dose": m.dose, "status": m.status} for m in medications],
        "labs": [{"id": l.id, "test_name": l.test_name, "value": l.value_numeric, "unit": l.unit, "observed_at": l.observed_at.isoformat()} for l in labs],
        "clinical_events": [{"id": e.id, "type": e.event_type, "date": e.event_date.isoformat() if e.event_date else None, "payload": e.payload} for e in events],
        "reports": [{"id": r.id, "filename": r.filename, "document_type": r.document_type, "processing_status": r.processing_status, "ocr_applied": r.ocr_applied, "uploaded_at": r.uploaded_at.isoformat()} for r in reports],
        "matches_count": len(matches)
    }

from pydantic import BaseModel

class CreatePatientRequest(BaseModel):
    external_patient_id: str
    sex: str | None = "UNKNOWN"
    date_of_birth: str | None = None
    source_system: str | None = None
    record_date: str | None = None

@app.post("/api/patients")
def create_patient(body: CreatePatientRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(Patient).filter(
        Patient.organization_id == user.organization_id,
        Patient.external_patient_id == body.external_patient_id.strip()
    ).first()
    if existing:
        return {"id": existing.id, "external_patient_id": existing.external_patient_id, "sex": existing.sex, "date_of_birth": existing.date_of_birth.isoformat() if existing.date_of_birth else None}

    dob = None
    if body.date_of_birth:
        try:
            dob = datetime.strptime(body.date_of_birth, "%Y-%m-%d").date()
        except ValueError:
            pass

    patient = Patient(
        organization_id=user.organization_id,
        external_patient_id=body.external_patient_id.strip(),
        sex=body.sex or "UNKNOWN",
        date_of_birth=dob,
        status="ACTIVE"
    )
    db.add(patient)
    db.flush()

    db.add(AuditLog(
        organization_id=user.organization_id,
        user_id=user.id,
        action="PATIENT_CREATED",
        entity_type="patient",
        entity_id=str(patient.id),
        metadata_json={"external_patient_id": patient.external_patient_id}
    ))
    db.commit()
    return {"id": patient.id, "external_patient_id": patient.external_patient_id, "sex": patient.sex, "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None}

@app.post("/api/patients/{patient_id}/reports")
async def upload_patient_report(
    patient_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(Patient.id == patient_id, Patient.organization_id == user.organization_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    file_bytes = await file.read()
    processor = ReportProcessorService()
    is_valid, err_msg = processor.validate_file(file.filename, file.content_type, len(file_bytes))
    if not is_valid:
        raise HTTPException(400, err_msg)

    upload_dir = os.path.join("uploads", "reports")
    os.makedirs(upload_dir, exist_ok=True)

    report = PatientReport(
        organization_id=user.organization_id,
        patient_id=patient_id,
        filename=file.filename,
        file_type=file.content_type or "application/octet-stream",
        processing_status="UPLOADED",
        extraction_status="PENDING",
        uploaded_at=datetime.utcnow()
    )
    db.add(report)
    db.flush()

    saved_filename = f"{report.id}_{file.filename}"
    saved_path = os.path.join(upload_dir, saved_filename)
    with open(saved_path, "wb") as f:
        f.write(file_bytes)
    report.file_path = saved_path

    try:
        raw_text, ocr_applied, doc_type = processor.extract_text(file_bytes, file.filename, file.content_type)
        report.raw_text = raw_text
        report.ocr_applied = ocr_applied
        report.document_type = doc_type
    except Exception:
        pass

    db.add(AuditLog(
        organization_id=user.organization_id,
        user_id=user.id,
        action="PATIENT_REPORT_UPLOADED",
        entity_type="patient_report",
        entity_id=str(report.id),
        metadata_json={"filename": file.filename, "patient_id": patient_id}
    ))
    db.commit()

    return {
        "report_id": report.id,
        "filename": report.filename,
        "processing_status": report.processing_status,
        "uploaded_at": report.uploaded_at.isoformat()
    }

@app.post("/api/patients/{patient_id}/reports/{report_id}/extract")
async def extract_patient_report(
    patient_id: int,
    report_id: int,
    file: UploadFile = File(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report = db.query(PatientReport).filter(
        PatientReport.id == report_id,
        PatientReport.patient_id == patient_id,
        PatientReport.organization_id == user.organization_id
    ).first()
    if not report:
        raise HTTPException(404, "Report not found")

    report.processing_status = "PROCESSING"
    db.commit()

    try:
        processor = ReportProcessorService()
        raw_text = report.raw_text
        ocr_applied = report.ocr_applied or False
        doc_type = report.document_type or "Clinical Report"

        if file is not None:
            file_bytes = await file.read()
            raw_text, ocr_applied, doc_type = processor.extract_text(file_bytes, report.filename, report.file_type)
        elif not raw_text or not raw_text.strip():
            if report.file_path and os.path.exists(report.file_path):
                with open(report.file_path, "rb") as f:
                    file_bytes = f.read()
                raw_text, ocr_applied, doc_type = processor.extract_text(file_bytes, report.filename, report.file_type)
            else:
                raise HTTPException(400, "File content or extracted text not found for this report.")

        # PII Anonymization - strictly fails if Presidio/spaCy unavailable
        try:
            anonymized_text = processor.anonymize_for_ai(raw_text)
        except Exception as pii_err:
            raise RuntimeError(f"PII anonymization error: {str(pii_err)}")

        extractor = ClinicalExtractorService()
        extracted_data = extractor.extract_clinical_info(anonymized_text, doc_type)

        report.document_type = doc_type
        report.ocr_applied = ocr_applied
        report.raw_text = anonymized_text
        report.extracted_json = extracted_data.model_dump()
        report.verified_json = extracted_data.model_dump()
        report.processing_status = "REVIEW_REQUIRED"
        report.extraction_status = "COMPLETED"
        report.error_message = None

        db.add(AuditLog(
            organization_id=user.organization_id,
            user_id=user.id,
            action="PATIENT_REPORT_EXTRACTED",
            entity_type="patient_report",
            entity_id=str(report.id),
            metadata_json={"ocr_applied": ocr_applied, "document_type": doc_type}
        ))
        db.commit()

        return {
            "report_id": report.id,
            "processing_status": report.processing_status,
            "extraction": report.extracted_json,
            "document_type": doc_type,
            "ocr_applied": ocr_applied
        }
    except Exception as e:
        report.processing_status = "FAILED"
        report.extraction_status = "FAILED"
        report.error_message = str(e)
        db.commit()

        is_pii_error = any(kw in str(e) for kw in ["spaCy", "Presidio", "anonymization", "PII"])
        stage = "pii_anonymization" if is_pii_error else "clinical_extraction"

        raise HTTPException(
            status_code=500,
            detail={
                "status": "failed",
                "stage": stage,
                "message": str(e)
            }
        )

@app.get("/api/patients/{patient_id}/reports/{report_id}/extraction")
def get_report_extraction(
    patient_id: int,
    report_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report = db.query(PatientReport).filter(
        PatientReport.id == report_id,
        PatientReport.patient_id == patient_id,
        PatientReport.organization_id == user.organization_id
    ).first()
    if not report:
        raise HTTPException(404, "Report not found")
    return {
        "report_id": report.id,
        "processing_status": report.processing_status,
        "document_type": report.document_type,
        "ocr_applied": report.ocr_applied,
        "extraction": report.verified_json or report.extracted_json
    }

@app.put("/api/patients/{patient_id}/reports/{report_id}/extraction")
def update_report_extraction(
    patient_id: int,
    report_id: int,
    payload: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    report = db.query(PatientReport).filter(
        PatientReport.id == report_id,
        PatientReport.patient_id == patient_id,
        PatientReport.organization_id == user.organization_id
    ).first()
    if not report:
        raise HTTPException(404, "Report not found")

    report.verified_json = payload
    db.commit()
    return {"status": "updated", "report_id": report.id}

@app.post("/api/patients/{patient_id}/reports/{report_id}/verify")
def verify_patient_report(
    patient_id: int,
    report_id: int,
    payload: dict = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(Patient.id == patient_id, Patient.organization_id == user.organization_id).first()
    report = db.query(PatientReport).filter(PatientReport.id == report_id, PatientReport.patient_id == patient_id).first()
    if not patient or not report:
        raise HTTPException(404, "Patient or Report not found")

    verified_data = payload or report.verified_json or report.extracted_json
    if not verified_data:
        raise HTTPException(400, "No extracted data available to verify")

    report.verified_json = verified_data
    report.processing_status = "VERIFIED"
    report.extraction_status = "COMPLETED"

    # Update patient demographics if present
    demog = verified_data.get("demographics", {})
    if demog.get("sex") and demog.get("sex") != "UNKNOWN":
        patient.sex = demog.get("sex")
    if demog.get("date_of_birth"):
        try:
            patient.date_of_birth = datetime.strptime(demog.get("date_of_birth"), "%Y-%m-%d").date()
        except ValueError:
            pass

    # Clear old report-derived records
    db.query(PatientCondition).filter(PatientCondition.patient_id == patient_id, PatientCondition.source == "clinical_report").delete()
    db.query(PatientMedication).filter(PatientMedication.patient_id == patient_id, PatientMedication.source == "clinical_report").delete()
    db.query(PatientLab).filter(PatientLab.patient_id == patient_id, PatientLab.source == "clinical_report").delete()
    db.query(ClinicalEvent).filter(ClinicalEvent.patient_id == patient_id, ClinicalEvent.source == "clinical_report").delete()

    # Add Diagnoses
    for d in verified_data.get("diagnoses", []):
        if d.get("condition_name"):
            db.add(PatientCondition(
                organization_id=user.organization_id,
                patient_id=patient_id,
                condition_name=d.get("condition_name").strip(),
                status="ACTIVE",
                source="clinical_report"
            ))

    # Add Comorbidities
    for c in verified_data.get("comorbidities", []):
        if c.get("condition_name"):
            db.add(PatientCondition(
                organization_id=user.organization_id,
                patient_id=patient_id,
                condition_name=c.get("condition_name").strip(),
                status="COMORBIDITY",
                source="clinical_report"
            ))

    # Add Medications
    for m in verified_data.get("medications", []):
        if m.get("name"):
            db.add(PatientMedication(
                organization_id=user.organization_id,
                patient_id=patient_id,
                medication_name=m.get("name").strip(),
                dose=m.get("dose"),
                route=m.get("route"),
                status=m.get("status", "current"),
                source="clinical_report"
            ))

    # Add Labs
    now = datetime.utcnow()
    for l in verified_data.get("laboratory_results", []):
        if l.get("test_name"):
            obs_at = now
            if l.get("observed_at"):
                try:
                    obs_at = datetime.strptime(l.get("observed_at"), "%Y-%m-%d")
                except ValueError:
                    pass
            db.add(PatientLab(
                organization_id=user.organization_id,
                patient_id=patient_id,
                test_name=l.get("test_name").strip(),
                value_numeric=l.get("value_numeric"),
                value_text=l.get("value_text"),
                unit=l.get("unit"),
                reference_range=l.get("reference_range"),
                observed_at=obs_at,
                source="clinical_report"
            ))

    # Add Clinical Events (ECOG, Biomarkers, Treatments, Stage)
    clin_status = verified_data.get("clinical_status", {})
    if clin_status.get("performance_status_ecog") is not None:
        db.add(ClinicalEvent(
            organization_id=user.organization_id,
            patient_id=patient_id,
            event_type=f"ECOG:{clin_status.get('performance_status_ecog')}",
            event_date=now,
            source="clinical_report",
            payload={"ecog": clin_status.get("performance_status_ecog")}
        ))

    for bm in verified_data.get("biomarkers", []):
        if bm.get("name"):
            db.add(ClinicalEvent(
                organization_id=user.organization_id,
                patient_id=patient_id,
                event_type=f"BIOMARKER:{bm.get('name').upper()}",
                event_date=now,
                source="clinical_report",
                payload={"name": bm.get("name"), "status": bm.get("status"), "value": bm.get("value")}
            ))

    for tr in verified_data.get("treatment_history", []):
        if tr.get("treatment_name"):
            db.add(ClinicalEvent(
                organization_id=user.organization_id,
                patient_id=patient_id,
                event_type=f"TREATMENT:{tr.get('treatment_type', 'GENERAL').upper()}",
                event_date=now,
                source="clinical_report",
                payload={"name": tr.get("treatment_name"), "response": tr.get("response")}
            ))

    db.add(AuditLog(
        organization_id=user.organization_id,
        user_id=user.id,
        action="PATIENT_REPORT_VERIFIED",
        entity_type="patient_report",
        entity_id=str(report.id),
        metadata_json={"patient_id": patient_id, "verified_by": user.email}
    ))
    db.commit()

    return {"status": "verified", "patient_id": patient_id, "report_id": report.id}

@app.post("/api/patients/{patient_id}/match")
def match_patient_trials(
    patient_id: int,
    limit: int = 10,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(Patient.id == patient_id, Patient.organization_id == user.organization_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    conditions = db.query(PatientCondition).filter(PatientCondition.patient_id == patient_id).all()
    query = " ".join(c.condition_name for c in conditions) or "Breast Cancer"
    trials = candidate_trials(db, query, limit=limit)

    engine = MatchingEngine(db)
    raw_results = []
    for t in trials:
        match = engine.screen(patient_id, t.id, user.organization_id)
        criteria_rows = db.query(MatchCriterionResult).filter(MatchCriterionResult.match_id == match.id).all()

        met_cnt = match.met_count or sum(1 for c in criteria_rows if c.decision == "MET")
        not_met_cnt = match.not_met_count or sum(1 for c in criteria_rows if c.decision == "NOT_MET")
        unk_cnt = match.unknown_count or sum(1 for c in criteria_rows if c.decision == "UNKNOWN")
        conf_cnt = match.conflicting_count or sum(1 for c in criteria_rows if c.decision == "CONFLICTING")
        total_crit = len(criteria_rows) or 1

        scr_cov = match.screening_coverage if match.screening_coverage is not None else round(((total_crit - unk_cnt) / total_crit) * 100.0, 1)
        ev_cov = round(((met_cnt + not_met_cnt) / total_crit) * 100.0, 1)

        why_ranked = []
        for c in criteria_rows:
            if c.decision == "MET":
                why_ranked.append(f"✓ {c.reason}")
            elif c.decision == "NOT_MET":
                why_ranked.append(f"✖ Exclusion: {c.reason}")
            else:
                why_ranked.append(f"⚠ {c.decision.title()}: {c.reason}")

        raw_results.append({
            "match_id": match.id,
            "trial_id": t.id,
            "nct_id": t.nct_id,
            "title": t.title,
            "status": match.status,
            "screening_coverage": scr_cov,
            "met_count": met_cnt,
            "not_met_count": not_met_cnt,
            "unknown_count": unk_cnt,
            "conflicting_count": conf_cnt,
            "evidence_coverage": ev_cov,
            "ranking_score": match.ranking_score,
            "explanation": match.explanation,
            "why_ranked_here": why_ranked,
            "criteria": [{
                "criterion_id": c.criterion_id,
                "decision": c.decision,
                "reason": c.reason,
                "evidence_source": c.evidence_source,
                "confidence": c.confidence
            } for c in criteria_rows]
        })

    # Rank results from best to worst using rank_trial_matches
    from backend.app.matching.engine import rank_trial_matches
    ranked_matches = rank_trial_matches(raw_results)

    return {
        "patient_id": patient_id,
        "total_candidates": len(trials),
        "returned": len(ranked_matches),
        "matches": ranked_matches
    }

@app.get("/api/trials/matches")
def get_trial_matches(
    patient_id: int,
    limit: int = 10,
    status_filter: str | None = None,
    min_coverage: float | None = None,
    recruiting_only: bool = False,
    sort_by: str = "best_match",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(Patient.id == patient_id, Patient.organization_id == user.organization_id).first()
    if not patient:
        raise HTTPException(404, "Patient not found")

    rows = db.query(MatchResult, Trial).join(Trial, Trial.id == MatchResult.trial_id).filter(
        MatchResult.patient_id == patient_id,
        MatchResult.organization_id == user.organization_id
    ).all()

    raw_results = []
    for match, t in rows:
        if recruiting_only and (not t.status or "RECRUIT" not in t.status.upper()):
            continue

        criteria_rows = db.query(MatchCriterionResult).filter(MatchCriterionResult.match_id == match.id).all()
        met_cnt = match.met_count or sum(1 for c in criteria_rows if c.decision == "MET")
        not_met_cnt = match.not_met_count or sum(1 for c in criteria_rows if c.decision == "NOT_MET")
        unk_cnt = match.unknown_count or sum(1 for c in criteria_rows if c.decision == "UNKNOWN")
        conf_cnt = match.conflicting_count or sum(1 for c in criteria_rows if c.decision == "CONFLICTING")
        total_crit = len(criteria_rows) or 1

        scr_cov = match.screening_coverage if match.screening_coverage is not None else round(((total_crit - unk_cnt) / total_crit) * 100.0, 1)
        ev_cov = round(((met_cnt + not_met_cnt) / total_crit) * 100.0, 1)

        if min_coverage and scr_cov < min_coverage:
            continue
        if status_filter and status_filter.upper() != "ALL" and match.status.upper() != status_filter.upper():
            continue

        why_ranked = []
        for c in criteria_rows:
            if c.decision == "MET":
                why_ranked.append(f"✓ {c.reason}")
            elif c.decision == "NOT_MET":
                why_ranked.append(f"✖ Exclusion: {c.reason}")
            else:
                why_ranked.append(f"⚠ {c.decision.title()}: {c.reason}")

        raw_results.append({
            "match_id": match.id,
            "trial_id": t.id,
            "nct_id": t.nct_id,
            "title": t.title,
            "recruitment_status": t.status,
            "updated_at": t.last_update_date.isoformat() if t.last_update_date else None,
            "status": match.status,
            "screening_coverage": scr_cov,
            "met_count": met_cnt,
            "not_met_count": not_met_cnt,
            "unknown_count": unk_cnt,
            "conflicting_count": conf_cnt,
            "evidence_coverage": ev_cov,
            "ranking_score": match.ranking_score,
            "explanation": match.explanation,
            "why_ranked_here": why_ranked,
            "criteria": [{
                "criterion_id": c.criterion_id,
                "decision": c.decision,
                "reason": c.reason,
                "evidence_source": c.evidence_source,
                "confidence": c.confidence
            } for c in criteria_rows]
        })

    from backend.app.matching.engine import rank_trial_matches
    ranked = rank_trial_matches(raw_results)

    if sort_by == "status":
        status_map = {"ELIGIBLE": 1, "REQUIRES_REVIEW": 2, "NOT_ELIGIBLE": 3}
        ranked.sort(key=lambda x: status_map.get(x["status"], 4))
    elif sort_by == "evidence_coverage":
        ranked.sort(key=lambda x: x["evidence_coverage"], reverse=True)
    elif sort_by == "updated_date":
        ranked.sort(key=lambda x: x["updated_at"] or "", reverse=True)

    return {
        "patient_id": patient_id,
        "total_candidates": len(rows),
        "returned": len(ranked[:limit]),
        "results": ranked[:limit]
    }

from backend.app.services.clinicaltrials_api import ClinicalTrialsAPIService

@app.post("/api/trials/sync")
def sync_trials(
    condition: str | None = "Breast Cancer",
    term: str | None = None,
    limit: int = 10,
    nct_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ClinicalTrialsAPIService(db)
    return service.sync_trials(condition=condition, term=term, limit=limit, nct_id=nct_id)

@app.get("/api/trials/metadata")
def trial_metadata(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ClinicalTrialsAPIService(db).get_metadata()

@app.get("/api/trials/search-areas")
def trial_search_areas(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ClinicalTrialsAPIService(db).get_search_areas()

@app.get("/api/trials/enums")
def trial_enums(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ClinicalTrialsAPIService(db).get_enums()

@app.get("/api/trials/stats/size")
def trial_stats_size(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ClinicalTrialsAPIService(db).get_stats_size()

@app.get("/api/trials/stats/field-values")
def trial_stats_field_values(field: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ClinicalTrialsAPIService(db).get_stats_field_values(field)

@app.get("/api/trials/stats/field-sizes")
def trial_stats_field_sizes(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return ClinicalTrialsAPIService(db).get_stats_field_sizes()

@app.get("/api/trials")
def trials(limit:int=50,cursor:int=0,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    limit=min(max(limit,1),100); rows=db.query(Trial).filter(Trial.id>cursor).order_by(Trial.id).limit(limit+1).all(); more=len(rows)>limit; rows=rows[:limit]
    return {"items":[{"id":t.id,"nct_id":t.nct_id,"title":t.title,"status":t.status,"phase":t.phase,"conditions":t.conditions or []} for t in rows],"next_cursor":rows[-1].id if more and rows else None,"has_more":more}

@app.get("/api/trials/{nct_id}")
def trial(
    nct_id: str,
    fetch_live: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ClinicalTrialsAPIService(db)
    t = db.query(Trial).filter(Trial.nct_id == nct_id).one_or_none()
    if not t or fetch_live:
        raw_study = service.fetch_single_study(nct_id)
        if raw_study:
            from backend.app.processors.trial_processor import TrialProcessor
            TrialProcessor(db).import_records([raw_study])
            t = db.query(Trial).filter(Trial.nct_id == nct_id).one_or_none()
    if not t:
        raise HTTPException(404, f"Trial with NCT ID '{nct_id}' not found")
    return {
        "id": t.id,
        "nct_id": t.nct_id,
        "title": t.title,
        "official_title": t.official_title,
        "status": t.status,
        "phase": t.phase,
        "conditions": t.conditions or [],
        "interventions": t.interventions or [],
        "min_age": t.min_age,
        "max_age": t.max_age,
        "sex": t.sex,
        "healthy_volunteers": t.healthy_volunteers,
        "study_type": t.study_type,
        "enrollment": t.enrollment,
        "locations": t.locations or [],
        "sponsor": t.sponsor,
        "eligibility_text": t.eligibility_text,
        "last_update_date": t.last_update_date.isoformat() if t.last_update_date else None
    }


@app.get("/api/patients/{patient_id}/candidates")
def patient_candidates(patient_id:int,limit:int=10,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    """Semantic candidate retrieval: build a query from the patient's structured
    conditions/medications and rank trials by lexical/embedding similarity, so the
    matching engine never has to score the full trial table for every patient."""
    p=db.query(Patient).filter(Patient.id==patient_id,Patient.organization_id==user.organization_id).one_or_none()
    if not p: raise HTTPException(404,"Patient not found")
    conditions=db.query(PatientCondition).filter(PatientCondition.patient_id==patient_id).all()
    query=" ".join(c.condition_name for c in conditions) or p.external_patient_id
    trials=candidate_trials(db,query,limit=min(max(limit,1),50))
    return {"query":query,"items":[{"id":t.id,"nct_id":t.nct_id,"title":t.title,"status":t.status,"phase":t.phase,"conditions":t.conditions or []} for t in trials]}

@app.post("/api/screening/{patient_id}/{trial_id}")
def screen(patient_id:int,trial_id:int,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    p=db.query(Patient).filter(Patient.id==patient_id,Patient.organization_id==user.organization_id).one_or_none()
    if not p: raise HTTPException(404,"Patient not found")
    m=MatchingEngine(db).screen(patient_id,trial_id,user.organization_id)
    rows=db.query(MatchCriterionResult).filter(MatchCriterionResult.match_id==m.id).all()
    return {"id":m.id,"status":m.status,"ranking_score":m.ranking_score,"evidence_completeness":m.evidence_completeness,"explanation":m.explanation,"criteria":[{"criterion_id":r.criterion_id,"decision":r.decision,"reason":r.reason,"evidence_source":r.evidence_source,"evidence_record_id":r.evidence_record_id,"confidence":r.confidence} for r in rows]}

@app.post("/api/patients/{patient_id}/labs")
def add_lab(patient_id:int,test_name:str,value:float,unit:str|None=None,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    p=db.query(Patient).filter(Patient.id==patient_id,Patient.organization_id==user.organization_id).one_or_none()
    if not p: raise HTTPException(404,"Patient not found")
    
    # Upsert logic: Update existing lab record for the same test_name if it exists
    existing_lab = db.query(PatientLab).filter(
        PatientLab.patient_id == patient_id,
        PatientLab.test_name.ilike(test_name.strip())
    ).first()

    if existing_lab:
        existing_lab.value_numeric = value
        if unit: existing_lab.unit = unit
        existing_lab.observed_at = datetime.utcnow()
        lab = existing_lab
    else:
        lab = PatientLab(
            organization_id=user.organization_id,
            patient_id=patient_id,
            test_name=test_name.strip(),
            value_numeric=value,
            unit=unit,
            observed_at=datetime.utcnow(),
            source="manual_demo"
        )
        db.add(lab)

    db.flush()
    db.add(ClinicalEvent(
        organization_id=user.organization_id,
        patient_id=patient_id,
        event_type=f"LAB:{test_name.lower()}",
        event_date=lab.observed_at,
        source="manual_demo",
        source_record_id=str(lab.id)
    ))
    trials = ChangeImpactService(db).impacted_trials(patient_id, user.organization_id, test_name)
    db.add(AuditLog(
        organization_id=user.organization_id,
        user_id=user.id,
        action="PATIENT_DATA_CHANGED",
        entity_type="patient",
        entity_id=str(patient_id),
        metadata_json={"concept": test_name, "value": value, "unit": unit, "affected_trials": trials}
    ))
    db.commit()
    return {"status": "updated" if existing_lab else "created", "lab_id": lab.id, "affected_trial_ids": trials}

@app.post("/api/patients/{patient_id}/notes")
def add_note(patient_id:int,text:str,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    """Accepts free-text clinical notes and anonymizes them with Presidio before
    persisting anything. Only the anonymized text and detected entity metadata are
    stored; the raw text supplied by the caller is discarded after processing."""
    p=db.query(Patient).filter(Patient.id==patient_id,Patient.organization_id==user.organization_id).one_or_none()
    if not p: raise HTTPException(404,"Patient not found")
    result=PresidioService().anonymize(text)
    note=PatientNote(organization_id=user.organization_id,patient_id=patient_id,anonymized_text=result["text"],detected_entities=result["entities"],anonymization_enabled=result["enabled"],author_user_id=user.id)
    db.add(note); db.flush()
    db.add(AuditLog(organization_id=user.organization_id,user_id=user.id,action="PATIENT_NOTE_ADDED",entity_type="patient_note",entity_id=str(note.id),metadata_json={"entities_detected":len(result["entities"]),"presidio_enabled":result["enabled"]}))
    db.commit()
    return {"id":note.id,"anonymized_text":note.anonymized_text,"detected_entities":note.detected_entities,"anonymization_enabled":note.anonymization_enabled}

@app.get("/api/matches/{patient_id}")
def matches(patient_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(MatchResult, Trial).join(Trial, Trial.id == MatchResult.trial_id).filter(
        MatchResult.patient_id == patient_id,
        MatchResult.organization_id == user.organization_id
    ).all()

    raw_results = []
    for m, t in rows:
        criteria_rows = db.query(MatchCriterionResult).filter(MatchCriterionResult.match_id == m.id).all()
        met_cnt = m.met_count or sum(1 for c in criteria_rows if c.decision == "MET")
        not_met_cnt = m.not_met_count or sum(1 for c in criteria_rows if c.decision == "NOT_MET")
        unk_cnt = m.unknown_count or sum(1 for c in criteria_rows if c.decision == "UNKNOWN")
        conf_cnt = m.conflicting_count or sum(1 for c in criteria_rows if c.decision == "CONFLICTING")
        total_crit = len(criteria_rows) or 1

        scr_cov = m.screening_coverage if m.screening_coverage is not None else round(((total_crit - unk_cnt) / total_crit) * 100.0, 1)
        ev_cov = round(((met_cnt + not_met_cnt) / total_crit) * 100.0, 1)

        why_ranked = []
        for c in criteria_rows:
            if c.decision == "MET":
                why_ranked.append(f"✓ {c.reason}")
            elif c.decision == "NOT_MET":
                why_ranked.append(f"✖ Exclusion: {c.reason}")
            else:
                why_ranked.append(f"⚠ {c.decision.title()}: {c.reason}")

        raw_results.append({
            "id": m.id,
            "match_id": m.id,
            "trial_id": t.id,
            "nct_id": t.nct_id,
            "title": t.title,
            "recruitment_status": t.status,
            "updated_at": t.last_update_date.isoformat() if t.last_update_date else None,
            "status": m.status,
            "score": m.ranking_score,
            "ranking_score": m.ranking_score,
            "evidence_completeness": m.evidence_completeness,
            "screening_coverage": scr_cov,
            "evidence_coverage": ev_cov,
            "met_count": met_cnt,
            "not_met_count": not_met_cnt,
            "unknown_count": unk_cnt,
            "conflicting_count": conf_cnt,
            "explanation": m.explanation,
            "why_ranked_here": why_ranked,
            "criteria": [{
                "criterion_id": c.criterion_id,
                "decision": c.decision,
                "reason": c.reason,
                "evidence_source": c.evidence_source,
                "confidence": c.confidence
            } for c in criteria_rows]
        })

    from backend.app.matching.engine import rank_trial_matches
    return rank_trial_matches(raw_results)

from backend.app.services.document_generator import MatchDocumentGenerator

@app.get("/api/matches/document/{match_id}")
def match_document(match_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    gen = MatchDocumentGenerator(db)
    doc = gen.build_report(match_id, user.organization_id)
    if not doc:
        raise HTTPException(404, "Match document not found for this evaluation")
    return doc

from backend.app.services.dashboard import overview as get_dashboard_overview

@app.get("/api/dashboard/overview")
def dashboard_overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_dashboard_overview(db, user.organization_id)

@app.get("/api/notifications")
def notifications(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    rows=db.query(Notification).filter(Notification.user_id==user.id).order_by(Notification.created_at.desc()).limit(50).all()
    return [{"id":n.id,"type":n.type,"title":n.title,"message":n.message,"severity":n.severity,"read":n.read_at is not None} for n in rows]

@app.get("/api/audit")
def audit(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    rows=db.query(AuditLog).filter(AuditLog.organization_id==user.organization_id).order_by(AuditLog.created_at.desc()).limit(100).all()
    return [{"id":x.id,"action":x.action,"entity_type":x.entity_type,"entity_id":x.entity_id,"metadata":x.metadata_json,"created_at":x.created_at.isoformat()} for x in rows]

@app.post("/api/jobs/{job_id}/process")
def process_job(job_id:int,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    job=db.query(ScreeningJob).filter(ScreeningJob.id==job_id,ScreeningJob.organization_id==user.organization_id).one_or_none()
    if not job: raise HTTPException(404,"Job not found")
    result = process_one(db,job_id)
    return {"id":result.id,"status":result.status}

from backend.app.services.monitoring import monitoring_overview

@app.get("/api/monitoring/overview")
def get_monitoring_overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return monitoring_overview(db, user.organization_id)

@app.get("/api/monitoring/cron")
def monitoring_cron(x_cron_secret:str|None=Header(default=None),db:Session=Depends(get_db)):
    # Vercel cron calls this route. Keep it lightweight; durable workers belong outside Vercel.
    if x_cron_secret and x_cron_secret != s.cron_secret: raise HTTPException(401,"Invalid cron secret")
    queued=db.query(ScreeningJob).filter(ScreeningJob.status=="QUEUED").order_by(ScreeningJob.created_at).limit(5).all()
    processed=[]
    for job in queued: processed.append(process_one(db,job.id).id)
    return {"processed":processed}
