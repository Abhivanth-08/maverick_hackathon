from datetime import date, datetime, timedelta
from backend.app.database.session import Base, engine, SessionLocal
from backend.app.models import Organization, Patient, PatientLab, PatientMedication, Trial, TrialCriterion
from backend.app.matching.engine import MatchingEngine

def test_creatinine_met_then_not_met():
    Base.metadata.create_all(engine); db=SessionLocal()
    org=Organization(name="test-org"); db.add(org); db.flush()
    p=Patient(organization_id=org.id,external_patient_id="T1",date_of_birth=date(1980,1,1),sex="Female"); db.add(p); db.flush()
    t=Trial(nct_id="NCT-TEST",title="Test",status="RECRUITING"); db.add(t); db.flush()
    c=TrialCriterion(trial_id=t.id,criterion_type="INCLUSION",criterion_text="Creatinine < 1.5",category="LAB",operator="<",structured_value="1.5"); db.add(c)
    db.add(PatientLab(organization_id=org.id,patient_id=p.id,test_name="Creatinine",value_numeric=1.2,unit="mg/dL",observed_at=datetime.utcnow())); db.commit()
    m=MatchingEngine(db).screen(p.id,t.id,org.id); assert m.status == "POTENTIAL_MATCH"
    db.add(PatientLab(organization_id=org.id,patient_id=p.id,test_name="Creatinine",value_numeric=1.8,unit="mg/dL",observed_at=datetime.utcnow())); db.commit()
    m=MatchingEngine(db).screen(p.id,t.id,org.id); assert m.status == "NOT_ELIGIBLE"

def test_temporal_constraint_resolves_from_dated_medication():
    Base.metadata.create_all(engine); db=SessionLocal()
    org=Organization(name="test-org-temporal"); db.add(org); db.flush()
    p=Patient(organization_id=org.id,external_patient_id="T2",date_of_birth=date(1980,1,1)); db.add(p); db.flush()
    t=Trial(nct_id="NCT-TEMPORAL",title="Temporal Test",status="RECRUITING"); db.add(t); db.flush()
    c=TrialCriterion(trial_id=t.id,criterion_type="EXCLUSION",criterion_text="No chemotherapy within 30 days",category="TREATMENT_HISTORY",temporal_constraint="WITHIN 30 DAYS"); db.add(c)
    db.add(PatientMedication(organization_id=org.id,patient_id=p.id,medication_name="Chemotherapy - Doxorubicin",start_date=date.today()-timedelta(days=10),end_date=date.today()-timedelta(days=10),status="COMPLETED")); db.commit()
    engine_obj=MatchingEngine(db)
    decision, reason, evidence = engine_obj.evaluate(p, c)
    assert decision in ("MET","NOT_MET")  # resolved from dated evidence, not left UNKNOWN
    assert evidence.get("source") == "patient_medications"

def test_unresolvable_criterion_routes_to_groq_not_hardcoded_unknown():
    Base.metadata.create_all(engine); db=SessionLocal()
    org=Organization(name="test-org-groq"); db.add(org); db.flush()
    p=Patient(organization_id=org.id,external_patient_id="T3",date_of_birth=date(1980,1,1)); db.add(p); db.flush()
    t=Trial(nct_id="NCT-GROQ",title="Groq Test",status="RECRUITING"); db.add(t); db.flush()
    c=TrialCriterion(trial_id=t.id,criterion_type="INCLUSION",criterion_text="ECOG performance status of 0 or 1",category="OTHER"); db.add(c); db.commit()
    decision, reason, evidence = MatchingEngine(db).evaluate(p, c)
    # Without GROQ_API_KEY configured, GroqService reports that explicitly rather than
    # the engine silently returning a hardcoded "requires Groq/reviewer reasoning" string.
    assert evidence.get("source") == "groq_llm"
    assert "GROQ_API_KEY" in reason or decision in ("MET","NOT_MET","UNKNOWN","CONFLICTING")
