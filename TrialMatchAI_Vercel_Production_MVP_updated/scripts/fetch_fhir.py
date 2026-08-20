import sys
import os
from pathlib import Path
import requests
from datetime import date, datetime
import json

# Ensure we can import from backend
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.database.session import Base, engine, SessionLocal
from backend.app.models import *

def fetch_and_seed_fhir():
    db = SessionLocal()
    org = db.query(Organization).filter_by(name="Demo Research Organization").one_or_none()
    if not org:
        org = Organization(name="Demo Research Organization")
        db.add(org)
        db.flush()

    fhir_base = "http://hapi.fhir.org/baseR4"
    print(f"Fetching data from {fhir_base}...")
    
    # We fetch 50 recent patients and their conditions and observations
    resp = requests.get(f"{fhir_base}/Patient?_sort=-_lastUpdated&_count=50&_revinclude=Condition:patient&_revinclude=Observation:patient")
    if resp.status_code != 200:
        print(f"Failed to fetch data: {resp.status_code}")
        return
        
    bundle = resp.json()
    entries = bundle.get('entry', [])
    
    # Map FHIR IDs to DB Patient objects
    patient_map = {}
    
    for entry in entries:
        resource = entry.get('resource', {})
        res_type = resource.get('resourceType')
        
        if res_type == 'Patient':
            pid = resource.get('id')
            ext_id = f"FHIR-{pid}"
            
            gender = resource.get('gender', 'UNKNOWN').capitalize()
            dob_str = resource.get('birthDate')
            dob = None
            if dob_str:
                try:
                    dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
                except ValueError:
                    pass
                    
            p = db.query(Patient).filter_by(organization_id=org.id, external_patient_id=ext_id).one_or_none()
            if not p:
                p = Patient(organization_id=org.id, external_patient_id=ext_id, date_of_birth=dob, sex=gender)
                db.add(p)
                db.flush()
            patient_map[pid] = p
            print(f"Added/Found Patient: {ext_id}")

    for entry in entries:
        resource = entry.get('resource', {})
        res_type = resource.get('resourceType')
        
        if res_type == 'Condition':
            subject = resource.get('subject', {}).get('reference', '')
            if subject.startswith('Patient/'):
                pid = subject.split('/')[1]
                p = patient_map.get(pid)
                if p:
                    code_concept = resource.get('code', {})
                    text = code_concept.get('text')
                    if not text:
                        codings = code_concept.get('coding', [])
                        if codings:
                            text = codings[0].get('display')
                    
                    if text:
                        # check if exists
                        c = db.query(PatientCondition).filter_by(patient_id=p.id, condition_name=text).first()
                        if not c:
                            cond = PatientCondition(
                                organization_id=org.id,
                                patient_id=p.id,
                                condition_name=text,
                                status="ACTIVE",
                                source="fhir"
                            )
                            db.add(cond)
                            print(f"Added condition '{text}' for {p.external_patient_id}")
                            
        elif res_type == 'Observation':
            subject = resource.get('subject', {}).get('reference', '')
            if subject.startswith('Patient/'):
                pid = subject.split('/')[1]
                p = patient_map.get(pid)
                if p:
                    code_concept = resource.get('code', {})
                    text = code_concept.get('text')
                    if not text:
                        codings = code_concept.get('coding', [])
                        if codings:
                            text = codings[0].get('display')
                            
                    val_quantity = resource.get('valueQuantity', {})
                    val_num = val_quantity.get('value')
                    unit = val_quantity.get('unit')
                    
                    eff_date_str = resource.get('effectiveDateTime')
                    obs_at = datetime.utcnow()
                    if eff_date_str:
                        try:
                            # Might have timezone or just be YYYY-MM-DD
                            obs_at = datetime.fromisoformat(eff_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                        except:
                            pass

                    if text and val_num is not None:
                        lab = db.query(PatientLab).filter_by(patient_id=p.id, test_name=text).first()
                        if not lab:
                            new_lab = PatientLab(
                                organization_id=org.id,
                                patient_id=p.id,
                                test_name=text,
                                value_numeric=val_num,
                                unit=unit,
                                observed_at=obs_at,
                                source="fhir"
                            )
                            db.add(new_lab)
                            print(f"Added observation '{text}' = {val_num} {unit} for {p.external_patient_id}")
    
    db.commit()
    print("Successfully fetched real-time FHIR data and inserted into database.")

if __name__ == "__main__":
    fetch_and_seed_fhir()
