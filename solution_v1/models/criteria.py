from pydantic import BaseModel
from typing import List, Optional, Any

class CriterionNode(BaseModel):
    id: str
    type: str
    concept: str
    operator: str
    value: Any
    unit: Optional[str] = None
    mandatory: bool = True
    timeframe_days: Optional[int] = None

class StructuredCriteria(BaseModel):
    nct_id: str
    inclusion: List[CriterionNode]
    exclusion: List[CriterionNode]