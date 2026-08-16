import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datetime import date, datetime, timedelta
from backend.app.database.session import Base, engine, SessionLocal
from backend.app.models import *
from backend.app.core.security import hash_password
Base.metadata.create_all(engine)
db=SessionLocal()
org=db.query(Organization).filter_by(name="Demo Research Organization").one_or_none() or Organization(name="Demo Research Organization")
db.add(org); db.flush() if org.id is None else None
u=db.query(User).filter_by(email="researcher@trialmatch.ai").one_or_none()
if not u: db.add(User(organization_id=org.id,email="researcher@trialmatch.ai",password_hash=hash_password("Demo123!"),role="RESEARCHER"))
p=db.query(Patient).filter_by(organization_id=org.id,external_patient_id="P001").one_or_none()
if not p:
    p=Patient(organization_id=org.id,external_patient_id="P001",date_of_birth=date(1988,5,12),sex="Female"); db.add(p); db.flush()
    db.add(PatientCondition(organization_id=org.id,patient_id=p.id,condition_name="Breast Cancer",status="ACTIVE",source="synthea"))
    db.add(PatientLab(organization_id=org.id,patient_id=p.id,test_name="Creatinine",value_numeric=1.2,unit="mg/dL",observed_at=datetime.utcnow()-timedelta(days=1),source="synthea"))
    db.add(PatientLab(organization_id=org.id,patient_id=p.id,test_name="Hemoglobin",value_numeric=13.2,unit="g/dL",observed_at=datetime.utcnow()-timedelta(days=2),source="synthea"))
    db.add(ClinicalEvent(organization_id=org.id,patient_id=p.id,event_type="LAB:creatinine",event_date=datetime.utcnow()-timedelta(days=1),source="synthea"))
    # Seeded 10 days ago so the temporal engine's "no chemotherapy within 30 days"
    # exclusion criterion has real dated evidence to reason over instead of falling
    # straight through to Groq for lack of data.
    db.add(PatientMedication(organization_id=org.id,patient_id=p.id,medication_name="Chemotherapy - Doxorubicin",dose="60mg/m2",route="IV",start_date=(date.today()-timedelta(days=10)),end_date=(date.today()-timedelta(days=10)),status="COMPLETED",source="synthea"))
trial=db.query(Trial).filter_by(nct_id="NCT-DEMO-001").one_or_none()
if not trial:
    trial=Trial(nct_id="NCT-DEMO-001",title="Demo Oncology Trial",status="RECRUITING",phase="PHASE2",conditions=["Breast Cancer"],interventions=["Demo Intervention"],eligibility_text="INCLUSION\nAge >= 18; Breast Cancer; Creatinine < 1.5\nEXCLUSION\nNo chemotherapy within 30 days")
    db.add(trial); db.flush()
    db.add_all([
      TrialCriterion(trial_id=trial.id,criterion_type="INCLUSION",criterion_text="Age >= 18",category="AGE",operator=">=",structured_value="18",unit="YEARS",confidence=.99),
      TrialCriterion(trial_id=trial.id,criterion_type="INCLUSION",criterion_text="Breast Cancer",category="DIAGNOSIS",confidence=.8),
      TrialCriterion(trial_id=trial.id,criterion_type="INCLUSION",criterion_text="Creatinine < 1.5",category="LAB",operator="<",structured_value="1.5",unit="mg/dL",confidence=.99),
      TrialCriterion(trial_id=trial.id,criterion_type="EXCLUSION",criterion_text="No chemotherapy within 30 days",category="TREATMENT_HISTORY",temporal_constraint="WITHIN 30 DAYS",confidence=.7),
      TrialCriterion(trial_id=trial.id,criterion_type="INCLUSION",criterion_text="ECOG performance status of 0 or 1",category="OTHER",confidence=.6)
    ])
db.commit(); print("Demo ready: researcher@trialmatch.ai / Demo123!")
