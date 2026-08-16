# Vercel-friendly MVP: persist jobs in PostgreSQL. A durable external worker/queue should process
# large jobs in production; Vercel functions are request/response compute, not a persistent worker.
from sqlalchemy.orm import Session
from backend.app.models import ScreeningJob
from backend.app.matching.engine import MatchingEngine

def process_one(db: Session, job_id: int):
    job=db.get(ScreeningJob,job_id)
    if not job: return None
    job.status="PROCESSING"; job.attempt_count += 1; db.commit()
    try:
        if job.trial_id is not None:
            MatchingEngine(db).screen(job.patient_id,job.trial_id,job.organization_id)
        job.status="COMPLETED"; db.commit()
    except Exception as exc:
        job.status="FAILED"; job.error_message=str(exc); db.commit()
    return job
