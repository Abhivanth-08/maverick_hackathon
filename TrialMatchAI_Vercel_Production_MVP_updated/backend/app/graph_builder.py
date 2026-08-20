import networkx as nx
from pyvis.network import Network
from sqlalchemy.orm import Session
from backend.app.models import Patient, PatientCondition, PatientMedication, PatientLab, ClinicalEvent
import tempfile
import os

def generate_patient_graph_html(db: Session, patient_id: int) -> str:
    """
    Builds a NetworkX knowledge graph for the patient and returns the PyVis HTML string.
    """
    patient = db.get(Patient, patient_id)
    if not patient:
        return "<h3>Patient not found</h3>"
        
    G = nx.Graph()
    
    # Root Node
    root_id = f"Patient_{patient.id}"
    label = f"Patient {patient.external_patient_id}\n{patient.sex}, {patient.date_of_birth}"
    G.add_node(root_id, label=label, color="#4CAF50", shape="box", font={"color": "white", "size": 20})
    
    # Conditions
    conditions = db.query(PatientCondition).filter_by(patient_id=patient_id).all()
    for c in conditions:
        node_id = f"Cond_{c.id}"
        G.add_node(node_id, label=f"Condition:\n{c.condition_name}", color="#F44336", shape="ellipse")
        G.add_edge(root_id, node_id, label="HAS_CONDITION")
        
    # Medications
    meds = db.query(PatientMedication).filter_by(patient_id=patient_id).all()
    for m in meds:
        node_id = f"Med_{m.id}"
        G.add_node(node_id, label=f"Medication:\n{m.medication_name}\n{m.dose or ''}", color="#2196F3", shape="ellipse")
        G.add_edge(root_id, node_id, label="TAKES")
        
    # Labs
    labs = db.query(PatientLab).filter_by(patient_id=patient_id).all()
    for l in labs:
        node_id = f"Lab_{l.id}"
        val = f"{l.value_numeric} {l.unit or ''}"
        G.add_node(node_id, label=f"Lab:\n{l.test_name}\n{val}", color="#FF9800", shape="ellipse")
        G.add_edge(root_id, node_id, label="HAS_LAB")
        
    # Events
    events = db.query(ClinicalEvent).filter_by(patient_id=patient_id).all()
    for e in events:
        node_id = f"Event_{e.id}"
        G.add_node(node_id, label=f"Event:\n{e.event_type}\n{e.event_date}", color="#9C27B0", shape="ellipse")
        G.add_edge(root_id, node_id, label="HAD_EVENT")
        
    net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white", directed=True, cdn_resources="remote")
    net.from_nx(G)
    
    # Enable physics for better layout
    net.toggle_physics(True)
    
    # Save to a temporary file and read back
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
        net.save_graph(tmp.name)
        tmp.seek(0)
        html_content = tmp.read().decode("utf-8")
        
    os.unlink(tmp.name)
    return html_content
