import streamlit as st

st.set_page_config(page_title="Synapse-KG", layout="wide", initial_sidebar_state="expanded")

st.sidebar.title("Synapse-KG")
st.sidebar.markdown("**Neuro-Symbolic Clinical Trial Intelligence Platform**")
st.sidebar.markdown("---")
st.sidebar.success("✅ Application Loaded")

st.title("Synapse-KG")
st.markdown("### AI interprets. Rules decide. Evidence proves.")
st.markdown("""
Welcome to Synapse-KG, the hackathon-grade clinical trial research assistant.

Use the sidebar to navigate through the application:
1. **Trial Search**: Find real clinical trials using the ClinicalTrials.gov API.
2. **Patient Screening**: Evaluate real patients from public FHIR APIs against trial criteria.
3. **Knowledge Graph**: Visualize patient facts and relationships.
4. **Audit Trail**: View deterministic evaluations and explanations.
""")