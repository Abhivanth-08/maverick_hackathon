import networkx as nx
from models.patient import Patient

def build_patient_graph(patient: Patient) -> nx.Graph:
    G = nx.Graph()
    p_node = f"Patient {patient.id}"
    G.add_node(p_node, label="Patient", title=p_node, color="lightblue", size=30)
    
    for fact in patient.facts:
        f_node = fact.id
        label = f"{fact.display}"
        if fact.value:
            label += f"\n{fact.value} {fact.unit or ''}"
            
        color = "lightgreen" if fact.resource_type == "Observation" else "lightcoral"
        G.add_node(f_node, label=fact.resource_type, title=label, color=color, size=20)
        G.add_edge(p_node, f_node, label=f"HAS_{fact.resource_type.upper()}")
        
    return G