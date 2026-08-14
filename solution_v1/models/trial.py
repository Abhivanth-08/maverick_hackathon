from pydantic import BaseModel
from typing import List, Optional

class Trial(BaseModel):
    nct_id: str
    title: str
    condition: str
    intervention: str
    status: str
    phase: str
    study_type: str
    location: str
    eligibility_criteria_text: str