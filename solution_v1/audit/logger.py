from db.database import SessionLocal, AuditEvent
from models.evidence import EvaluationTrace

def log_evaluation(patient_id: str, trial_id: str, trace: EvaluationTrace, overall_decision: str):
    db = SessionLocal()
    event = AuditEvent(
        patient_id=patient_id,
        trial_id=trial_id,
        criterion_id=trace.criterion_id,
        source_id=trace.evidence_source.source if trace.evidence_source else "None",
        rule=f"{trace.concept} {trace.operator} {trace.target_value}",
        evaluation_result=str(trace.evaluation_result),
        decision=trace.status
    )
    db.add(event)
    db.commit()
    db.close()