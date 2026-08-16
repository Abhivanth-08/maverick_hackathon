from sqlalchemy.orm import Session
from backend.app.models import TrialCriterion, ScreeningJob, MatchResult

class ChangeImpactService:
    """Dependency-aware incremental re-screening for changed clinical concepts."""
    def __init__(self, db: Session): self.db=db
    def impacted_trials(self, patient_id: int, organization_id: int, concept: str):
        criteria=self.db.query(TrialCriterion).filter(TrialCriterion.criterion_text.ilike(f"%{concept}%")).all()
        trial_ids=sorted({c.trial_id for c in criteria})
        matches=self.db.query(MatchResult).filter(MatchResult.patient_id==patient_id,MatchResult.trial_id.in_(trial_ids),MatchResult.organization_id==organization_id).all() if trial_ids else []
        for m in matches:
            self.db.add(ScreeningJob(organization_id=organization_id,patient_id=patient_id,trial_id=m.trial_id,job_type="PATIENT_RESCREEN",status="QUEUED"))
        self.db.commit()
        return trial_ids
