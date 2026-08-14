from pydantic import BaseModel
from typing import Any, Optional
from models.patient import PatientFact

class EvaluationTrace(BaseModel):
    criterion_id: str
    criterion_type: str
    concept: str
    operator: str
    target_value: Any
    patient_value: Any = None
    evidence_source: Optional[PatientFact] = None
    evaluation_result: bool
    status: str
    message: str