import requests
from utils.config import FHIR_BASE_URL
from models.patient import Patient, PatientFact
from datetime import datetime

def parse_fhir_date(date_str):
    if not date_str:
        return None
    try:
        if len(date_str) == 4:
             return datetime(int(date_str), 1, 1).date()
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
    except:
        return None

def fetch_patients(name: str = None, count: int = 5):
    url = f"{FHIR_BASE_URL}/Patient"
    params = {"_count": count}
    if name:
        params["name"] = name
        
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        bundle = resp.json()
        patients = []
        for entry in bundle.get("entry", []):
            res = entry.get("resource", {})
            p_id = res.get("id")
            gender = res.get("gender", "unknown")
            birthDate = res.get("birthDate")
            
            p = Patient(id=p_id, gender=gender, birthDate=parse_fhir_date(birthDate))
            patients.append(p)
        return patients
    except Exception as e:
        print(f"FHIR fetch error: {e}")
        return []

def fetch_patient_facts(patient_id: str):
    facts = []
    cond_url = f"{FHIR_BASE_URL}/Condition?patient={patient_id}"
    try:
        resp = requests.get(cond_url, timeout=5)
        if resp.status_code == 200:
            for entry in resp.json().get("entry", []):
                res = entry.get("resource", {})
                code_text = res.get("code", {}).get("text", "Unknown Condition")
                facts.append(PatientFact(
                    id=res.get("id", "unknown"), resource_type="Condition", code="cond", display=code_text,
                    timestamp=None, source=f"Condition/{res.get('id')}"
                ))
    except: pass
    
    obs_url = f"{FHIR_BASE_URL}/Observation?patient={patient_id}"
    try:
        resp = requests.get(obs_url, timeout=5)
        if resp.status_code == 200:
            for entry in resp.json().get("entry", []):
                res = entry.get("resource", {})
                code_text = res.get("code", {}).get("text", "Unknown Observation")
                val = res.get("valueQuantity", {}).get("value")
                unit = res.get("valueQuantity", {}).get("unit")
                facts.append(PatientFact(
                    id=res.get("id", "unknown"), resource_type="Observation", code="obs", display=code_text,
                    value=val, unit=unit, timestamp=None, source=f"Observation/{res.get('id')}"
                ))
    except: pass
    return facts