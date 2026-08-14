import streamlit as st
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
    st.info(f"Currently selected trial: {st.session_state['selected_trial'].nct_id}")