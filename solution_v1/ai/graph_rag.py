import json
from models.patient import Patient
from models.criteria import StructuredCriteria
from utils.config import GROQ_API_KEY, LLM_MODEL

def generate_graph_summary(patient: Patient) -> str:
    """
    Serializes the patient's knowledge graph (nodes/edges) into a text summary
    suitable for GraphRAG reasoning.
    """
    summary = f"Patient ID: {patient.id}\n"
    summary += f"Demographics: {patient.gender}, BirthDate: {patient.birthDate}\n\n"
    summary += "Graph Nodes and Relations:\n"
    for fact in patient.facts:
        summary += f"- Patient HAS_{fact.resource_type.upper()} -> {fact.display}"
        if fact.value is not None:
            summary += f" = {fact.value} {fact.unit or ''}"
        summary += "\n"
    return summary

def graph_rag_reasoning(patient: Patient, criteria: StructuredCriteria, deterministic_result: dict) -> str:
    """
    Implements GraphRAG reasoning: Uses the Patient Knowledge Graph and the structured criteria 
    to provide a natural language reasoning/explanation using the Groq LLM.
    """
    if not GROQ_API_KEY:
        return "GraphRAG Reasoning unavailable. Please set GROQ_API_KEY in the .env file."
        
    import groq
    client = groq.Groq(api_key=GROQ_API_KEY)
    
    graph_context = generate_graph_summary(patient)
    criteria_context = criteria.model_dump_json(indent=2)
    overall_status = deterministic_result.get('overall', 'UNKNOWN')
    
    prompt = f"""
    You are an AI research assistant performing GraphRAG (Graph Retrieval-Augmented Generation).
    Below is the structured Knowledge Graph of a patient, the criteria for a clinical trial, and the deterministic rule engine's conclusion.
    
    Your task is to provide a concise, medically sound reasoning explaining WHY the patient was marked as '{overall_status}'. 
    Only use the facts provided in the Patient Knowledge Graph. Do not invent data.

    [Patient Knowledge Graph Summary]
    {graph_context}
    
    [Trial Criteria]
    {criteria_context}
    
    [Rule Engine Decision]
    {overall_status}
    
    Reasoning:
    """
    
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"GraphRAG failed: {e}")
        return "Failed to generate GraphRAG reasoning due to API error."
