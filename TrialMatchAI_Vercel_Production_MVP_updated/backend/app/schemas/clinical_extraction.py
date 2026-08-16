from pydantic import BaseModel, Field
from typing import List, Optional

class DemographicsItem(BaseModel):
    age: Optional[int] = None
    date_of_birth: Optional[str] = None
    sex: Optional[str] = "UNKNOWN"

class DiagnosisItem(BaseModel):
    condition_name: str
    is_primary: bool = False
    stage: Optional[str] = None
    subtype: Optional[str] = None
    histology: Optional[str] = None
    source_text: Optional[str] = None
    page_number: Optional[int] = 1
    confidence: float = 0.95

class MedicationItem(BaseModel):
    name: str
    dose: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    status: Optional[str] = "current"
    start_date: Optional[str] = None
    stop_date: Optional[str] = None
    source_text: Optional[str] = None
    page_number: Optional[int] = 1
    confidence: float = 0.95

class LabItem(BaseModel):
    test_name: str
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    observed_at: Optional[str] = None
    source_text: Optional[str] = None
    page_number: Optional[int] = 1
    confidence: float = 0.95

class ClinicalStatusItem(BaseModel):
    performance_status_ecog: Optional[int] = None
    disease_status: Optional[str] = None
    treatment_status: Optional[str] = None

class TreatmentHistoryItem(BaseModel):
    treatment_name: str
    treatment_type: Optional[str] = None
    response: Optional[str] = None
    treatment_date: Optional[str] = None
    source_text: Optional[str] = None
    page_number: Optional[int] = 1
    confidence: float = 0.95

class ComorbidityItem(BaseModel):
    condition_name: str
    source_text: Optional[str] = None
    page_number: Optional[int] = 1
    confidence: float = 0.95

class AllergyItem(BaseModel):
    allergy_name: str
    reaction: Optional[str] = None
    source_text: Optional[str] = None
    page_number: Optional[int] = 1
    confidence: float = 0.95

class BiomarkerItem(BaseModel):
    name: str
    status: str = "UNKNOWN"
    value: Optional[str] = None
    source_text: Optional[str] = None
    page_number: Optional[int] = 1
    confidence: float = 0.95

class PatientClinicalExtraction(BaseModel):
    document_type: str = "Clinical Report"
    demographics: DemographicsItem = Field(default_factory=DemographicsItem)
    diagnoses: List[DiagnosisItem] = Field(default_factory=list)
    medications: List[MedicationItem] = Field(default_factory=list)
    laboratory_results: List[LabItem] = Field(default_factory=list)
    clinical_status: ClinicalStatusItem = Field(default_factory=ClinicalStatusItem)
    treatment_history: List[TreatmentHistoryItem] = Field(default_factory=list)
    comorbidities: List[ComorbidityItem] = Field(default_factory=list)
    allergies: List[AllergyItem] = Field(default_factory=list)
    biomarkers: List[BiomarkerItem] = Field(default_factory=list)
    clinical_notes: Optional[str] = None
