from pydantic import BaseModel
from typing import Literal
Decision = Literal["MET", "NOT_MET", "UNKNOWN", "CONFLICTING"]
class CriterionResultOut(BaseModel):
    criterion_id: int
    decision: Decision
    reason: str
    evidence_source: str | None = None
    evidence_record_id: str | None = None
    evidence_date: str | None = None
    confidence: float | None = None
class MatchOut(BaseModel):
    patient_id: int
    trial_id: int
    nct_id: str
    status: str
    ranking_score: float
    evidence_completeness: float
    explanation: str
    criteria: list[CriterionResultOut]
