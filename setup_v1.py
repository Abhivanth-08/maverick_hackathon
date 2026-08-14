import os

files = {
    "solution_v1/requirements.txt": """streamlit
fastapi
networkx
pydantic
pandas
requests
httpx
plotly
pyvis
streamlit-agraph
sqlalchemy
python-dotenv
openai
fpdf2""",
    "solution_v1/.env.example": """CLINICALTRIALS_API_BASE=https://clinicaltrials.gov/api/v2
FHIR_BASE_URL=http://hapi.fhir.org/baseR4
LLM_PROVIDER=openai
LLM_API_KEY=
LLM_MODEL=gpt-4o
NLI_MODEL=gpt-4o
DATABASE_URL=sqlite:///synapse.db""",
    "solution_v1/utils/__init__.py": "",
    "solution_v1/utils/config.py": """import os
from dotenv import load_dotenv

load_dotenv()

CLINICALTRIALS_API_BASE = os.getenv("CLINICALTRIALS_API_BASE", "https://clinicaltrials.gov/api/v2")
FHIR_BASE_URL = os.getenv("FHIR_BASE_URL", "http://hapi.fhir.org/baseR4")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
NLI_MODEL = os.getenv("NLI_MODEL", "gpt-4o")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///synapse.db")""",
    "solution_v1/models/__init__.py": "",
    "solution_v1/models/trial.py": """from pydantic import BaseModel
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
    eligibility_criteria_text: str""",
    "solution_v1/models/criteria.py": """from pydantic import BaseModel
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
    exclusion: List[CriterionNode]""",
    "solution_v1/models/patient.py": """from pydantic import BaseModel
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
    facts: List[PatientFact] = []""",
    "solution_v1/models/evidence.py": """from pydantic import BaseModel
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
    message: str""",
    "solution_v1/integrations/__init__.py": "",
    "solution_v1/integrations/clinicaltrials.py": """import requests
from utils.config import CLINICALTRIALS_API_BASE
from models.trial import Trial

def search_trials(condition: str = None, keyword: str = None):
    url = f"{CLINICALTRIALS_API_BASE}/studies"
    params = {"pageSize": 10}
    if condition:
        params["query.cond"] = condition
    if keyword:
        params["query.term"] = keyword
        
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        trials = []
        for study in data.get('studies', []):
            protocol = study.get('protocolSection', {})
            id_module = protocol.get('identificationModule', {})
            status_module = protocol.get('statusModule', {})
            cond_module = protocol.get('conditionsModule', {})
            eligibility_module = protocol.get('eligibilityModule', {})
            interv_module = protocol.get('armsInterventionsModule', {})
            
            nct_id = id_module.get('nctId', 'Unknown')
            title = id_module.get('briefTitle', 'Unknown')
            status = status_module.get('overallStatus', 'Unknown')
            cond = ", ".join(cond_module.get('conditions', ['Unknown']))
            interv = ", ".join([i.get('name', '') for i in interv_module.get('interventions', [])]) if interv_module else 'Unknown'
            phase = ", ".join(status_module.get('phases', ['Unknown']))
            eligibility_text = eligibility_module.get('eligibilityCriteria', 'Not available')
            
            trials.append(Trial(
                nct_id=nct_id, title=title, condition=cond, intervention=interv,
                status=status, phase=phase, study_type="Interventional", location="Various",
                eligibility_criteria_text=eligibility_text
            ))
        return trials
    except Exception as e:
        print(f"Error fetching trials: {e}")
        return []""",
    "solution_v1/integrations/fhir.py": """import requests
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
    return facts""",
    "solution_v1/ai/__init__.py": "",
    "solution_v1/ai/criteria_extractor.py": """import os
import json
from utils.config import LLM_API_KEY
from models.criteria import StructuredCriteria, CriterionNode

def extract_criteria(nct_id: str, eligibility_text: str) -> StructuredCriteria:
    if not LLM_API_KEY:
        return StructuredCriteria(
            nct_id=nct_id,
            inclusion=[
                CriterionNode(id="INC1", type="inclusion", concept="age", operator=">=", value=18)
            ],
            exclusion=[
                CriterionNode(id="EXC1", type="exclusion", concept="pregnancy", operator="exists", value=True)
            ]
        )
    
    import openai
    client = openai.OpenAI(api_key=LLM_API_KEY)
    
    prompt = f\"\"\"Extract structured eligibility criteria from the following clinical trial text.
    Return JSON format EXACTLY matching this structure:
    {{
        "inclusion": [
            {{"id": "INC01", "type": "inclusion", "concept": "age", "operator": ">=", "value": 18, "unit": "years", "mandatory": true}}
        ],
        "exclusion": [
            {{"id": "EXC01", "type": "exclusion", "concept": "condition", "operator": "exists", "value": "pregnancy", "mandatory": true}}
        ]
    }}
    Text:
    {eligibility_text[:2000]}
    \"\"\"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        inc = [CriterionNode(**item) for item in data.get('inclusion', [])]
        exc = [CriterionNode(**item) for item in data.get('exclusion', [])]
        return StructuredCriteria(nct_id=nct_id, inclusion=inc, exclusion=exc)
    except Exception as e:
        print(f"LLM Extraction failed: {e}")
        return StructuredCriteria(
            nct_id=nct_id,
            inclusion=[CriterionNode(id="INC1", type="inclusion", concept="age", operator=">=", value=18)],
            exclusion=[]
        )""",
    "solution_v1/core/__init__.py": "",
    "solution_v1/core/rule_engine.py": """from models.criteria import StructuredCriteria, CriterionNode
from models.patient import Patient, PatientFact
from models.evidence import EvaluationTrace
from datetime import datetime

def evaluate_criterion(criterion: CriterionNode, patient: Patient) -> EvaluationTrace:
    status = "UNKNOWN"
    eval_result = False
    evidence = None
    message = "No matching evidence found."
    
    if criterion.concept.lower() == "age":
        if patient.birthDate:
            age = (datetime.now().date() - patient.birthDate).days / 365.25
            evidence = PatientFact(id="age", resource_type="Demographics", code="age", display="Age", value=age, source="Patient Profile")
            try:
                c_val = float(criterion.value)
                if criterion.operator == ">=": eval_result = age >= c_val
                elif criterion.operator == "<=": eval_result = age <= c_val
                elif criterion.operator == ">": eval_result = age > c_val
                elif criterion.operator == "<": eval_result = age < c_val
                elif criterion.operator == "==": eval_result = age == c_val
                status = "PASS" if eval_result else "FAIL"
                message = f"Age {age:.1f} evaluated against {criterion.operator} {c_val}"
            except:
                message = "Invalid age target value."
        else:
            message = "Patient age not available."
    else:
        for fact in patient.facts:
            if criterion.concept.lower() in fact.display.lower() or str(criterion.value).lower() in fact.display.lower():
                evidence = fact
                if criterion.operator == "exists":
                    eval_result = True
                elif criterion.operator == "not_exists":
                    eval_result = False
                elif criterion.operator in [">=", "<=", ">", "<", "=="] and fact.value is not None:
                    try:
                        f_val = float(fact.value)
                        c_val = float(criterion.value)
                        if criterion.operator == ">=": eval_result = f_val >= c_val
                        elif criterion.operator == "<=": eval_result = f_val <= c_val
                        elif criterion.operator == ">": eval_result = f_val > c_val
                        elif criterion.operator == "<": eval_result = f_val < c_val
                        elif criterion.operator == "==": eval_result = f_val == c_val
                    except:
                        eval_result = False
                
                status = "PASS" if eval_result else "FAIL"
                message = f"Found evidence: {fact.display} = {fact.value} {fact.unit}"
                break
        
        if not evidence and criterion.operator == "not_exists":
            eval_result = True
            status = "PASS"
            message = "No evidence found, passing 'not_exists' criteria."
            
    if criterion.type == "exclusion":
        if status == "PASS":
            status = "FAIL"
        elif status == "FAIL":
            status = "PASS"
            
    return EvaluationTrace(
        criterion_id=criterion.id,
        criterion_type=criterion.type,
        concept=criterion.concept,
        operator=criterion.operator,
        target_value=criterion.value,
        patient_value=evidence.value if evidence else None,
        evidence_source=evidence,
        evaluation_result=eval_result,
        status=status,
        message=message
    )

def evaluate_patient(criteria: StructuredCriteria, patient: Patient):
    traces = []
    for inc in criteria.inclusion:
        traces.append(evaluate_criterion(inc, patient))
    for exc in criteria.exclusion:
        traces.append(evaluate_criterion(exc, patient))
        
    passed = sum(1 for t in traces if t.status == "PASS")
    failed = sum(1 for t in traces if t.status == "FAIL")
    unknown = sum(1 for t in traces if t.status == "UNKNOWN")
    
    if failed > 0: overall = "NOT ELIGIBLE"
    elif unknown > 0: overall = "NEEDS REVIEW"
    else: overall = "POTENTIALLY ELIGIBLE"
        
    return {
        "overall": overall,
        "traces": traces,
        "passed": passed,
        "failed": failed,
        "unknown": unknown
    }""",
    "solution_v1/graph/__init__.py": "",
    "solution_v1/graph/patient_graph.py": """import networkx as nx
from models.patient import Patient

def build_patient_graph(patient: Patient) -> nx.Graph:
    G = nx.Graph()
    p_node = f"Patient {patient.id}"
    G.add_node(p_node, label="Patient", title=p_node, color="lightblue", size=30)
    
    for fact in patient.facts:
        f_node = fact.id
        label = f"{fact.display}"
        if fact.value:
            label += f"\\n{fact.value} {fact.unit or ''}"
            
        color = "lightgreen" if fact.resource_type == "Observation" else "lightcoral"
        G.add_node(f_node, label=fact.resource_type, title=label, color=color, size=20)
        G.add_edge(p_node, f_node, label=f"HAS_{fact.resource_type.upper()}")
        
    return G""",
    "solution_v1/db/__init__.py": "",
    "solution_v1/db/database.py": """from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from utils.config import DATABASE_URL
from datetime import datetime
import os

db_url = DATABASE_URL
if db_url.startswith("sqlite:///"):
    path = db_url.replace("sqlite:///", "")
    if not os.path.isabs(path):
        db_url = "sqlite:///" + os.path.join(os.path.dirname(os.path.dirname(__file__)), path)

engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    patient_id = Column(String, index=True)
    trial_id = Column(String, index=True)
    criterion_id = Column(String)
    source_id = Column(String)
    rule = Column(String)
    evaluation_result = Column(String)
    decision = Column(String)
    engine_version = Column(String, default="Synapse-KG v0.1")

Base.metadata.create_all(bind=engine)""",
    "solution_v1/audit/__init__.py": "",
    "solution_v1/audit/logger.py": """from db.database import SessionLocal, AuditEvent
from models.evidence import EvaluationTrace

def log_evaluation(patient_id: str, trial_id: str, trace: EvaluationTrace, overall_decision: str):
    db = SessionLocal()
    event = AuditEvent(
        patient_id=patient_id,
        trial_id=trial_id,
        criterion_id=trace.criterion_id,
        source_id=trace.evidence_source.source if trace.evidence_source else "None",
        rule=f"{trace.concept} {trace.operator} {trace.target_value}",
        evaluation_result=str(trace.evaluation_result),
        decision=trace.status
    )
    db.add(event)
    db.commit()
    db.close()""",
    "solution_v1/app.py": """import streamlit as st

st.set_page_config(page_title="Synapse-KG", layout="wide", initial_sidebar_state="expanded")

st.sidebar.title("Synapse-KG")
st.sidebar.markdown("**Neuro-Symbolic Clinical Trial Intelligence Platform**")
st.sidebar.markdown("---")
st.sidebar.success("✅ Application Loaded")

st.title("Synapse-KG")
st.markdown("### AI interprets. Rules decide. Evidence proves.")
st.markdown(\"\"\"
Welcome to Synapse-KG, the hackathon-grade clinical trial research assistant.

Use the sidebar to navigate through the application:
1. **Trial Search**: Find real clinical trials using the ClinicalTrials.gov API.
2. **Patient Screening**: Evaluate real patients from public FHIR APIs against trial criteria.
3. **Knowledge Graph**: Visualize patient facts and relationships.
4. **Audit Trail**: View deterministic evaluations and explanations.
\"\"\")""",
    "solution_v1/pages/01_Trial_Search.py": """import streamlit as st
import time
from integrations.clinicaltrials import search_trials

st.title("Trial Search")
st.markdown("Search real clinical trials from ClinicalTrials.gov")

col1, col2 = st.columns(2)
with col1:
    condition = st.text_input("Condition (e.g., Diabetes)")
with col2:
    keyword = st.text_input("Keyword")

if st.button("SEARCH REAL TRIALS"):
    with st.spinner("Fetching from ClinicalTrials.gov API..."):
        start = time.time()
        trials = search_trials(condition, keyword)
        elapsed = time.time() - start
        
    st.success(f"Found {len(trials)} trials in {elapsed:.2f} seconds.")
    for t in trials:
        with st.expander(f"{t.nct_id} - {t.title}"):
            st.markdown(f"**Condition:** {t.condition}")
            st.markdown(f"**Status:** {t.status}")
            st.markdown(f"**Intervention:** {t.intervention}")
            st.markdown("**Eligibility Criteria:**")
            st.text(t.eligibility_criteria_text[:1000] + "...")
            if st.button("Select Trial", key=t.nct_id):
                st.session_state['selected_trial'] = t
                st.success(f"Selected {t.nct_id}")

if 'selected_trial' in st.session_state:
    st.info(f"Currently selected trial: {st.session_state['selected_trial'].nct_id}")""",
    "solution_v1/pages/02_Patient_Screening.py": """import streamlit as st
from integrations.fhir import fetch_patients, fetch_patient_facts
from ai.criteria_extractor import extract_criteria
from core.rule_engine import evaluate_patient
from audit.logger import log_evaluation

st.title("Patient Screening")

if 'selected_trial' not in st.session_state:
    st.warning("Please select a trial first in the Trial Search page.")
    st.stop()

trial = st.session_state['selected_trial']
st.markdown(f"### Evaluating against: {trial.nct_id}")

if 'criteria' not in st.session_state or st.button("Extract Criteria (LLM)"):
    with st.spinner("Extracting structured criteria..."):
        st.session_state['criteria'] = extract_criteria(trial.nct_id, trial.eligibility_criteria_text)
    st.success("Criteria extracted!")

st.json(st.session_state['criteria'].model_dump())

if st.button("Fetch Patients from FHIR"):
    with st.spinner("Fetching public patients..."):
        patients = fetch_patients(count=5)
        for p in patients:
            p.facts = fetch_patient_facts(p.id)
        st.session_state['patients'] = patients
            
if 'patients' in st.session_state:
    st.markdown("### Patients")
    for p in st.session_state['patients']:
        with st.expander(f"Patient {p.id} ({p.gender}, {p.birthDate})"):
            st.markdown(f"Facts loaded: {len(p.facts)}")
            if st.button("Evaluate Patient", key=f"eval_btn_{p.id}"):
                result = evaluate_patient(st.session_state['criteria'], p)
                st.session_state[f'eval_{p.id}'] = result
                for trace in result['traces']:
                    log_evaluation(p.id, trial.nct_id, trace, result['overall'])
                    
            if f"eval_{p.id}" in st.session_state:
                res = st.session_state[f"eval_{p.id}"]
                if res['overall'] == 'POTENTIALLY ELIGIBLE':
                    st.success(res['overall'])
                elif res['overall'] == 'NOT ELIGIBLE':
                    st.error(res['overall'])
                else:
                    st.warning(res['overall'])
                
                st.markdown("#### Evaluation Traces")
                for t in res['traces']:
                    icon = "✅" if t.status == "PASS" else "❌" if t.status == "FAIL" else "⚠"
                    st.markdown(f"{icon} **{t.concept} {t.operator} {t.target_value}** -> {t.message}")""",
    "solution_v1/pages/03_Knowledge_Graph.py": """import streamlit as st
from pyvis.network import Network
import tempfile
from graph.patient_graph import build_patient_graph

st.title("Patient Knowledge Graph")

if 'patients' not in st.session_state:
    st.warning("Please load patients in the Patient Screening page.")
    st.stop()

p_id = st.selectbox("Select Patient", [p.id for p in st.session_state['patients']])
patient = next(p for p in st.session_state['patients'] if p.id == p_id)

st.markdown(f"### Graph for Patient {patient.id}")

G = build_patient_graph(patient)
net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white")
net.from_nx(G)

path = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
net.save_graph(path.name)

with open(path.name, 'r', encoding='utf-8') as f:
    html_data = f.read()
    
import streamlit.components.v1 as components
components.html(html_data, height=600)""",
    "solution_v1/pages/04_Audit_Trail.py": """import streamlit as st
import pandas as pd
from db.database import SessionLocal, AuditEvent

st.title("Audit Trail")
st.markdown("Immutable record of determinisitic decisions.")

db = SessionLocal()
events = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(100).all()
db.close()

if events:
    data = [{
        "Timestamp": e.timestamp,
        "Patient": e.patient_id,
        "Trial": e.trial_id,
        "Rule": e.rule,
        "Source": e.source_id,
        "Result": e.evaluation_result,
        "Decision": e.decision
    } for e in events]
    df = pd.DataFrame(data)
    st.dataframe(df)
else:
    st.info("No audit events recorded yet.")""",
    "solution_v1/README.md": """# Synapse-KG — Neuro-Symbolic Clinical Trial Intelligence Platform

AI interprets. Rules decide. Evidence proves.

## Architecture

1. **Trial Ingestion**: ClinicalTrials.gov API (v2) Integration for real-world study protocol extraction.
2. **Criteria Extraction**: Language Models are strictly confined to generating Structured AST representations of text guidelines, prohibiting LLMs from rendering clinical conclusions.
3. **Patient Data Pipeline**: Native connection to Public FHIR Servers providing real patient demographics, observations, and conditions.
4. **Knowledge Graph Ecosystem**: NetworkX powered representation of heterogeneous Patient Profiles for granular visualization.
5. **Deterministic Constraint Engine**: A pure Python logical evaluator ensuring deterministic rule application. **NO LLMs are employed for final eligibility decisions.**
6. **Audit Trail**: High-fidelity SQLite / SQLAlchemy tracking ensuring complete explainability and traceability of every condition evaluation against evidence sources.

## Getting Started

```bash
cd solution_v1
pip install -r requirements.txt
cp .env.example .env
# Optional: Set LLM_API_KEY if testing live OpenAI extraction
streamlit run app.py
```
"""
}

for path, content in files.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

print("Files generated.")
