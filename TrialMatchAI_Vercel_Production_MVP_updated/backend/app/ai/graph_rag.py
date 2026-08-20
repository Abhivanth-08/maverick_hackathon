import json
from sqlalchemy.orm import Session
from backend.app.models import Patient, PatientCondition, PatientMedication, PatientLab, ClinicalEvent, MatchResult, Trial
from backend.app.core.config import get_settings

def generate_graph_summary(db: Session, patient_id: int) -> str:
    """
    Serializes the patient's knowledge graph (nodes/edges) into a text summary
    suitable for GraphRAG reasoning.
    """
    patient = db.get(Patient, patient_id)
    if not patient:
        return ""
        
    summary = f"Patient ID: {patient.id}\n"
    summary += f"Demographics: Sex: {patient.sex}, BirthDate: {patient.date_of_birth}\n\n"
    summary += "Graph Nodes and Relations:\n"
    
    conditions = db.query(PatientCondition).filter_by(patient_id=patient_id).all()
    for c in conditions:
        summary += f"- Patient HAS_CONDITION -> {c.condition_name} (Status: {c.status})\n"
        
    meds = db.query(PatientMedication).filter_by(patient_id=patient_id).all()
    for m in meds:
        summary += f"- Patient HAS_MEDICATION -> {m.medication_name} (Dose: {m.dose})\n"
        
    labs = db.query(PatientLab).filter_by(patient_id=patient_id).all()
    for l in labs:
        summary += f"- Patient HAS_LAB -> {l.test_name} = {l.value_numeric} {l.unit or ''}\n"
        
    events = db.query(ClinicalEvent).filter_by(patient_id=patient_id).all()
    for e in events:
        summary += f"- Patient HAS_EVENT -> {e.event_type} on {e.event_date}\n"
        
    return summary

def generate_graph_rag_reasoning(db: Session, match_id: int) -> str:
    """
    Implements GraphRAG reasoning: Uses the Patient Knowledge Graph and the structured match result
    to provide a natural language reasoning/explanation using the Groq LLM.
    """
    settings = get_settings()
    if not settings.groq_api_key:
        return "GraphRAG Reasoning unavailable. Please set GROQ_API_KEY."
        
    import groq
    client = groq.Groq(api_key=settings.groq_api_key)
    
    match = db.get(MatchResult, match_id)
    if not match:
        return "Match result not found."
        
    trial = db.get(Trial, match.trial_id)
    
    graph_context = generate_graph_summary(db, match.patient_id)
    overall_status = match.status
    explanation = match.explanation
    
    prompt = f"""
    You are an AI research assistant performing GraphRAG (Graph Retrieval-Augmented Generation).
    Below is the structured Knowledge Graph of a patient, the trial details, and the deterministic rule engine's conclusion.
    
    Your task is to provide a concise, medically sound reasoning explaining WHY the patient was marked as '{overall_status}'. 
    Only use the facts provided in the Patient Knowledge Graph. Do not invent data.

    [Patient Knowledge Graph Summary]
    {graph_context}
    
    [Trial Title]
    {trial.title if trial else 'Unknown'}
    
    [Rule Engine Decision]
    Status: {overall_status}
    Details: {explanation}
    
    Reasoning:
    """
    
    try:
        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Failed to generate GraphRAG reasoning: {str(e)}"
