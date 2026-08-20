import sys
import os
sys.path.insert(0, os.getcwd())

from backend.app.database.session import SessionLocal
from backend.app.main import match_patient_trials
from backend.app.models import User, Patient, PatientCondition, PatientLab, PatientMedication, ClinicalEvent

db = SessionLocal()
user = db.query(User).first()
print(f"User: {user.email}, Org ID: {user.organization_id}")

patient = db.query(Patient).filter(Patient.id == 5).first()
if not patient:
    print("Patient 5 not found, listing available patients:")
    for p in db.query(Patient).all():
        print(f" - Patient ID {p.id}: {p.external_patient_id}")
else:
    print(f"Patient 5 found: {patient.external_patient_id}")
    try:
        res = match_patient_trials(5, 10, user, db)
        print("Match result count:", res["matches_count"])
        for m in res["matches"]:
            print(f"  Trial: {m['nct_id']} | Status: {m['status']} | Score: {m['ranking_score']}")
    except Exception as e:
        import traceback
        traceback.print_exc()
