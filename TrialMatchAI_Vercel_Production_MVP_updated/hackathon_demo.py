import streamlit as st
import requests
import json
import os
import time

st.set_page_config(page_title="Synapse-KG Hackathon Demo", layout="wide", page_icon="🧬")

# Configuration
API_BASE = "http://127.0.0.1:8000/api"
st.session_state.setdefault("token", None)
st.session_state.setdefault("patient_id", 1) # Use seeded patient P001

def login():
    if not st.session_state.token:
        try:
            resp = requests.post(f"{API_BASE}/auth/login", json={"email": "researcher@trialmatch.ai", "password": "Demo123!"})
            if resp.status_code == 200:
                st.session_state.token = resp.json()["access_token"]
        except Exception as e:
            st.error(f"Backend offline: {e}")

login()

def get_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}

st.sidebar.title("🧬 Synapse-KG")
st.sidebar.markdown("### Hackathon Prototype")
page = st.sidebar.radio("Navigation", ["1. Trial Selection", "2. Screening & GraphRAG", "3. Dynamic Simulation"])

if page == "1. Trial Selection":
    st.title("Step 1: Clinical Trial Selection")
    st.markdown("Choose whether to manually input a trial criteria or fetch scraped trials from ClinicalTrials.gov.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Manual Input")
        manual_title = st.text_input("Trial Title", "Custom Diabetes Trial")
        manual_criteria = st.text_area("Eligibility Criteria", "INCLUSION:\nAge >= 18\nHbA1c < 7.0\n\nEXCLUSION:\nPregnancy")
        if st.button("Use Manual Trial"):
            st.session_state.selected_trial = {"title": manual_title, "criteria": manual_criteria, "nct_id": "MANUAL-001"}
            st.success("Manual Trial loaded into session!")
            
    with col2:
        st.subheader("Scraped / Seeded Trials")
        if st.session_state.token:
            resp = requests.get(f"{API_BASE}/trials", headers=get_headers())
            if resp.status_code == 200:
                trials = resp.json().get("items", [])
                for t in trials:
                    with st.expander(f"{t['nct_id']} - {t['title']}"):
                        st.write(f"Status: {t['status']}")
                        if st.button("Select this Trial", key=f"sel_{t['id']}"):
                            st.session_state.selected_trial = {"title": t['title'], "nct_id": t['nct_id'], "trial_id": t['id']}
                            st.success(f"Selected {t['nct_id']}")
            else:
                st.error("Failed to fetch trials")

elif page == "2. Screening & GraphRAG":
    st.title("Step 2: Neuro-Symbolic Engine & GraphRAG")
    
    if "selected_trial" not in st.session_state:
        st.warning("Please select a trial in Step 1.")
        st.stop()
        
    st.markdown(f"**Target Trial:** {st.session_state.selected_trial['nct_id']} - {st.session_state.selected_trial['title']}")
    
    patient_id = st.session_state.patient_id
    
    colA, colB = st.columns([1, 1])
    
    with colA:
        st.subheader("Patient Knowledge Graph")
        try:
            # Fetch interactive Graph HTML
            graph_resp = requests.get(f"{API_BASE}/patients/{patient_id}/graph", headers=get_headers())
            if graph_resp.status_code == 200:
                import streamlit.components.v1 as components
                components.html(graph_resp.text, height=500)
        except Exception:
            st.warning("Could not load graph from backend.")
            
    with colB:
        st.subheader("Matching & Reasoning")
        if "trial_id" in st.session_state.selected_trial:
            tid = st.session_state.selected_trial["trial_id"]
            if st.button("Run Deterministic Match (Engine)"):
                with st.spinner("Processing AST Rules against Knowledge Graph..."):
                    match_resp = requests.post(f"{API_BASE}/screening/{patient_id}/{tid}", headers=get_headers())
                    if match_resp.status_code == 200:
                        res = match_resp.json()
                        st.session_state.last_match = res
                        st.success("Match complete.")
        
        if "last_match" in st.session_state:
            res = st.session_state.last_match
            status_color = "green" if res['status'] == "ELIGIBLE" else "red" if res['status'] == "NOT_ELIGIBLE" else "orange"
            st.markdown(f"<h3 style='color: {status_color}'>{res['status']}</h3>", unsafe_allow_html=True)
            
            st.markdown("#### Evaluation Traces")
            for crit in res.get("criteria", []):
                icon = "✅" if crit["decision"] == "MET" else "❌" if crit["decision"] == "NOT_MET" else "⚠️"
                st.write(f"{icon} {crit['reason']}")
                
            st.markdown("---")
            if st.button("Generate GraphRAG Explanation"):
                with st.spinner("Groq LLM is analyzing the Graph + Traces..."):
                    rag_resp = requests.get(f"{API_BASE}/patients/{patient_id}/graph_rag/{res['id']}", headers=get_headers())
                    if rag_resp.status_code == 200:
                        st.info(rag_resp.json().get("reasoning", "No reasoning returned."))

elif page == "3. Dynamic Simulation":
    st.title("Step 3: Dynamic Data Simulation")
    st.markdown("Simulate an incoming HL7/FHIR update (e.g., a new Lab Result). We will update the patient's record, which instantly alters the graph and the deterministic eligibility!")
    
    patient_id = st.session_state.patient_id
    
    st.subheader("Add New Patient Observation")
    test_name = st.text_input("Lab Test Name", "Creatinine")
    test_val = st.number_input("Value", value=2.5)
    test_unit = st.text_input("Unit", "mg/dL")
    
    if st.button("Simulate Incoming Data"):
        with st.spinner("Updating Knowledge Graph..."):
            resp = requests.post(
                f"{API_BASE}/patients/{patient_id}/labs",
                params={"test_name": test_name, "value": test_val, "unit": test_unit},
                headers=get_headers()
            )
            if resp.status_code == 200:
                st.success(f"Graph Updated: {test_name} = {test_val} {test_unit}")
                st.info("Go back to Step 2 and re-run the matching engine to see how the eligibility changed deterministically!")
            else:
                st.error("Failed to update.")
