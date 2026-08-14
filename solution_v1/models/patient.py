from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import date, datetime

class PatientFact(BaseModel):
    id: str
    resource_type: str
    code: str
    display: str
    value: Any = None
    unit: Optional[str] = None
    timestamp: Optional[datetime] = None
    source: str

class Patient(BaseModel):
    id: str
    gender: str
    birthDate: Optional[date]
    facts: List[PatientFact] = []