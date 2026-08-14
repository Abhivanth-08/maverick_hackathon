import streamlit as st
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
components.html(html_data, height=600)