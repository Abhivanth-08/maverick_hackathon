import streamlit as st
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
    st.info("No audit events recorded yet.")