import streamlit as st
from integrations.fhir import fetch_patients, fetch_patient_facts
from ai.criteria_extractor import extract_criteria
from core.rule_engine import evaluate_patient
from audit.logger import log_evaluation
from ai.graph_rag import graph_rag_reasoning

st.title("Patient Screening & GraphRAG")

if 'selected_trial' not in st.session_state:
    st.warning("Please select a trial first in the Trial Search page.")
    st.stop()

trial = st.session_state['selected_trial']
st.markdown(f"### Evaluating against: {trial.nct_id}")

if 'criteria' not in st.session_state or st.button("Extract Criteria (LLM)"):
    with st.spinner("Extracting structured criteria securely..."):
        st.session_state['criteria'] = extract_criteria(trial.nct_id, trial.eligibility_criteria_text)
    st.success("Criteria extracted and PII redacted (if any) via Microsoft Presidio!")

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
                    
                # Generate GraphRAG Reasoning
                with st.spinner("Generating GraphRAG reasoning..."):
                    rag_reasoning = graph_rag_reasoning(p, st.session_state['criteria'], result)
                    st.session_state[f'rag_{p.id}'] = rag_reasoning
                    
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
                    st.markdown(f"{icon} **{t.concept} {t.operator} {t.target_value}** -> {t.message}")

                if f"rag_{p.id}" in st.session_state:
                    st.markdown("---")
                    st.markdown("#### GraphRAG Reasoning")
                    st.info(st.session_state[f"rag_{p.id}"])