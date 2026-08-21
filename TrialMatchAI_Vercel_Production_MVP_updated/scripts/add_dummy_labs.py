import sys
import os
from datetime import datetime
from backend.app.database.session import SessionLocal
from backend.app.models import Patient, PatientLab, PatientCondition

db = SessionLocal()
patients = db.query(Patient).all()
for p in patients:
    labs = db.query(PatientLab).filter_by(patient_id=p.id).count()
    if labs == 0:
        print(f"Adding mock labs to {p.external_patient_id}")
        db.add(PatientLab(organization_id=p.organization_id, patient_id=p.id, test_name="Hemoglobin", value_numeric=14.2, unit="g/dL", observed_at=datetime.utcnow(), source="mock"))
        db.add(PatientLab(organization_id=p.organization_id, patient_id=p.id, test_name="Creatinine", value_numeric=1.1, unit="mg/dL", observed_at=datetime.utcnow(), source="mock"))
        db.add(PatientLab(organization_id=p.organization_id, patient_id=p.id, test_name="Platelets", value_numeric=250, unit="10^3/uL", observed_at=datetime.utcnow(), source="mock"))
        
    conds = db.query(PatientCondition).filter_by(patient_id=p.id).count()
    if conds == 0:
        db.add(PatientCondition(organization_id=p.organization_id, patient_id=p.id, condition_name="Type 2 Diabetes", status="ACTIVE", source="mock"))
        
db.commit()
print("Done.")
