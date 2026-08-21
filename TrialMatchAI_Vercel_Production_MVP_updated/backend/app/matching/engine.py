import re
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.app.models import Patient, PatientCondition, PatientMedication, PatientLab, ClinicalEvent, Trial, TrialCriterion, MatchResult, MatchCriterionResult, PatientNote, PatientReport
from backend.app.ai.groq_service import GroqService

def rank_trial_match_key(m: Dict[str, Any]) -> Tuple:
    """Deterministic ranking function implementing Section 3 priority rules:
    1. ELIGIBLE first
       - highest MET count
       - highest evidence coverage
       - highest ranking score
    2. REQUIRES_REVIEW second
       - fewest UNKNOWN count
       - highest MET count
       - highest evidence coverage
       - highest ranking score
    3. NOT_ELIGIBLE last
       - fewest NOT_MET count
       - highest MET count
       - highest ranking score
    """
    status = m.get("status", "REQUIRES_REVIEW")
    status_order = {"ELIGIBLE": 1, "REQUIRES_REVIEW": 2, "NOT_ELIGIBLE": 3}
    st = status_order.get(status, 4)

    met_count = m.get("met_count", 0)
    not_met_count = m.get("not_met_count", 0)
    unknown_count = m.get("unknown_count", 0)
    evidence_coverage = m.get("evidence_coverage", 0.0)
    ranking_score = m.get("ranking_score", 0.0)

    if status == "ELIGIBLE":
        return (st, -met_count, -evidence_coverage, -ranking_score)
    elif status == "REQUIRES_REVIEW":
        return (st, unknown_count, -met_count, -evidence_coverage, -ranking_score)
    else:  # NOT_ELIGIBLE
        return (st, not_met_count, -met_count, -ranking_score)

def rank_trial_matches(matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sorts candidate trial match results and assigns 1-based rank."""
    sorted_matches = sorted(matches, key=rank_trial_match_key)
    for idx, m in enumerate(sorted_matches, start=1):
        m["rank"] = idx
    return sorted_matches

class MatchingEngine:
    VERSION = "1.2.0"

    def __init__(self, db: Session):
        self.db = db
        self.groq = GroqService()

    def screen(self, patient_id: int, trial_id: int, organization_id: int) -> MatchResult:
        patient = self.db.get(Patient, patient_id)
        trial = self.db.get(Trial, trial_id)
        if not patient or not trial:
            raise ValueError("Patient or trial not found")

        criteria = self.db.query(TrialCriterion).filter_by(trial_id=trial_id).all()
        results = []
        for c in criteria:
            decision, reason, evidence = self.evaluate(patient, c)
            results.append((c, decision, reason, evidence))

        total_criteria = len(results) or 1
        met_count = sum(1 for _, d, _, _ in results if d == "MET")
        not_met_count = sum(1 for _, d, _, _ in results if d == "NOT_MET")
        unknown_count = sum(1 for _, d, _, _ in results if d == "UNKNOWN")
        conflicting_count = sum(1 for _, d, _, _ in results if d == "CONFLICTING")

        # Status determination rules (Section 2 & 4)
        if not_met_count > 0:
            status = "NOT_ELIGIBLE"
        elif met_count > 0 and unknown_count == 0 and conflicting_count == 0:
            status = "ELIGIBLE"
        else:
            status = "REQUIRES_REVIEW"

        # Coverage metrics (Section 5 & 6)
        screening_coverage = round(((total_criteria - unknown_count) / total_criteria) * 100.0, 1)
        evidence_coverage = round(((met_count + not_met_count) / total_criteria) * 100.0, 1)

        # Internal ranking score (Section 7)
        base_score = (met_count * 10) - (unknown_count * 4) - (conflicting_count * 20) - (not_met_count * 30)
        evidence_bonus = sum(2 for _, _, _, e in results if e.get("source") in ("patient_labs", "patient_conditions", "patient_medications", "clinical_events"))
        recruitment_bonus = 5 if trial.status and "RECRUIT" in trial.status.upper() else 0
        raw_score = float(base_score + evidence_bonus + recruitment_bonus)
        max_possible = float((total_criteria * 10) + (total_criteria * 2) + 5) if total_criteria > 0 else 1.0
        ranking_score = max(0.0, min(1.0, raw_score / max_possible))

        explanation = f"{met_count} criteria met; {not_met_count} not met; {unknown_count} unknown. Screening coverage: {screening_coverage}%."

        match = self.db.query(MatchResult).filter_by(
            patient_id=patient_id, trial_id=trial_id, organization_id=organization_id
        ).one_or_none()

        if not match:
            match = MatchResult(
                organization_id=organization_id,
                patient_id=patient_id,
                trial_id=trial_id,
                status=status,
                evidence_completeness=screening_coverage / 100.0,
                ranking_score=ranking_score,
                met_count=met_count,
                not_met_count=not_met_count,
                unknown_count=unknown_count,
                conflicting_count=conflicting_count,
                screening_coverage=screening_coverage,
                explanation=explanation,
                engine_version=self.VERSION
            )
            self.db.add(match)
            self.db.flush()
        else:
            match.status = status
            match.evidence_completeness = screening_coverage / 100.0
            match.ranking_score = ranking_score
            match.met_count = met_count
            match.not_met_count = not_met_count
            match.unknown_count = unknown_count
            match.conflicting_count = conflicting_count
            match.screening_coverage = screening_coverage
            match.explanation = explanation

            self.db.query(MatchCriterionResult).filter_by(match_id=match.id).delete()

        for c, d, r, e in results:
            ev_date = e.get('date')
            if isinstance(ev_date, str):
                try:
                    ev_date = datetime.fromisoformat(ev_date)
                except ValueError:
                    ev_date = None

            conf = e.get('confidence')
            if conf is not None:
                if isinstance(conf, str):
                    conf_lower = conf.strip().lower()
                    if conf_lower == 'high':
                        conf = 0.9
                    elif conf_lower == 'medium':
                        conf = 0.7
                    elif conf_lower == 'low':
                        conf = 0.4
                    else:
                        try:
                            conf = float(conf)
                        except ValueError:
                            conf = 0.8
                elif not isinstance(conf, (int, float)):
                    conf = 0.8

            self.db.add(MatchCriterionResult(
                match_id=match.id,
                criterion_id=c.id,
                decision=d,
                reason=r,
                evidence_source=e.get('source'),
                evidence_record_id=e.get('id'),
                evidence_date=ev_date,
                confidence=conf
            ))

        self.db.commit()
        return match

    def evaluate(self, patient: Patient, c: TrialCriterion) -> Tuple[str, str, Dict[str, Any]]:
        t = c.criterion_text.lower()
        evidence: Dict[str, Any] = {}

        # 1. AGE evaluation
        if c.category == "AGE" or "age" in t or "years" in t:
            if not patient.date_of_birth:
                return "UNKNOWN", "Date of birth is missing in patient records", evidence
            age = (date.today() - patient.date_of_birth).days / 365.2425
            m = re.search(r"(\d+(?:\.\d+)?)", t)
            if not m:
                return "UNKNOWN", "Age threshold could not be structured safely", evidence
            threshold = float(m.group(1))
            if ">=" in t or "at least" in t or "greater than" in t or ">= " in t:
                ok = age >= threshold
            elif "<=" in t or "under" in t or "less than" in t or "<" in t:
                ok = age <= threshold
            else:
                ok = age >= threshold
            return ("MET" if ok else "NOT_MET", f"Patient age is {age:.1f} years; required threshold {threshold}.", {"source": "patient_profile", "confidence": 1.0})

        # 2. HER2 / BIOMARKER evaluation
        if "her2" in t:
            # Look for HER2 in PatientLab, PatientNote, PatientReport verified_json
            labs = self.db.query(PatientLab).filter(PatientLab.patient_id == patient.id, PatientLab.test_name.ilike("%her2%")).all()
            reports = self.db.query(PatientReport).filter(PatientReport.patient_id == patient.id).all()
            
            her2_status = None
            for lab in labs:
                val_text = (lab.value_text or "").lower()
                if "positive" in val_text or "+" in val_text:
                    her2_status = "positive"
                elif "negative" in val_text or "-" in val_text:
                    her2_status = "negative"

            if not her2_status:
                for rep in reports:
                    vjson = rep.verified_json or rep.extracted_json or {}
                    bms = vjson.get("biomarkers", [])
                    for bm in bms:
                        if "her2" in str(bm.get("name", "")).lower():
                            her2_status = str(bm.get("status", "")).lower()

            if her2_status:
                requires_positive = "positive" in t or "+" in t or "overexpressed" in t
                requires_negative = "negative" in t or "-" in t
                if requires_positive:
                    ok = (her2_status == "positive")
                    return ("MET" if ok else "NOT_MET", f"Patient HER2 is {her2_status.upper()}; trial requires HER2 Positive.", {"source": "patient_biomarkers", "confidence": 0.98})
                elif requires_negative:
                    ok = (her2_status == "negative")
                    return ("MET" if ok else "NOT_MET", f"Patient HER2 is {her2_status.upper()}; trial requires HER2 Negative.", {"source": "patient_biomarkers", "confidence": 0.98})

        # 3. LAB THRESHOLD evaluation (Creatinine, Hemoglobin, WBC, Platelets, AST, ALT)
        lab_names = ["creatinine", "hemoglobin", "wbc", "platelets", "ast", "alt", "bilirubin"]
        matched_lab = next((l for l in lab_names if l in t), None)
        if c.category == "LAB" or matched_lab:
            name = matched_lab or "creatinine"
            lab = self.db.query(PatientLab).filter(
                PatientLab.patient_id == patient.id,
                PatientLab.test_name.ilike(f"%{name}%")
            ).order_by(PatientLab.observed_at.desc()).first()

            if not lab or lab.value_numeric is None:
                return "UNKNOWN", f"No recorded {name} laboratory evidence found", evidence

            m_val = re.search(r"(?:<|<=|>|>=|less than|below|at least|greater than)\s*([\d\.]+)", t)
            if m_val:
                threshold = float(m_val.group(1))
                val = lab.value_numeric
                if "<=" in t or "less than" in t or "below" in t or "<" in t:
                    ok = val <= threshold
                elif ">=" in t or "at least" in t or "greater than" in t or ">" in t:
                    ok = val >= threshold
                else:
                    ok = val <= threshold
                return ("MET" if ok else "NOT_MET", f"Latest {name.capitalize()}: {val} {lab.unit or ''}; required threshold {threshold}.", {"source": "patient_labs", "id": str(lab.id), "date": lab.observed_at.isoformat() if lab.observed_at else None, "confidence": 0.98})

        # 4. ECOG / PERFORMANCE STATUS evaluation
        if "ecog" in t or "performance status" in t:
            reports = self.db.query(PatientReport).filter(PatientReport.patient_id == patient.id).all()
            ecog_val = None
            for rep in reports:
                vjson = rep.verified_json or rep.extracted_json or {}
                cstat = vjson.get("clinical_status", {})
                if cstat.get("performance_status_ecog") is not None:
                    ecog_val = cstat.get("performance_status_ecog")

            if ecog_val is not None:
                m_ecog = re.search(r"([0-4])", t)
                max_ecog = int(m_ecog.group(1)) if m_ecog else 1
                ok = (ecog_val <= max_ecog)
                return ("MET" if ok else "NOT_MET", f"Patient ECOG status is {ecog_val}; maximum allowed is {max_ecog}.", {"source": "clinical_report", "confidence": 0.95})

        # 5. DIAGNOSIS / CONDITION evaluation
        if c.category == "DIAGNOSIS" or "cancer" in t or "carcinoma" in t:
            conds = self.db.query(PatientCondition).filter(PatientCondition.patient_id == patient.id).all()
            hit = next((x for x in conds if any(w in x.condition_name.lower() for w in t.split() if len(w) > 4)), None)
            if hit:
                return "MET", f"Matching condition evidence: {hit.condition_name}", {"source": "patient_conditions", "id": str(hit.id), "confidence": 0.95}

        # 6. TEMPORAL / MEDICATION evaluation
        if c.category in ("TREATMENT_HISTORY", "MEDICATION") and c.temporal_constraint:
            decision, reason, ev = self._evaluate_temporal(patient, c)
            if decision != "UNKNOWN":
                return decision, reason, ev

        # 7. Fallback to Groq LLM reasoning for unstructured criteria
        return self._evaluate_with_groq(patient, c)

    def _evaluate_temporal(self, patient: Patient, c: TrialCriterion):
        t = c.criterion_text.lower()
        constraint = (c.temporal_constraint or "").lower()
        m = re.search(r"(within|after|before)\s+(\d+)\s+(day|week|month|year)s?", constraint)
        if not m:
            return "UNKNOWN", "Temporal constraint could not be structured safely", {}
        direction, amount, unit = m.group(1), int(m.group(2)), m.group(3)
        days = amount * {"day": 1, "week": 7, "month": 30, "year": 365}[unit]

        keywords = [w for w in t.split() if len(w) > 4]
        events = self.db.query(ClinicalEvent).filter(ClinicalEvent.patient_id == patient.id).order_by(ClinicalEvent.event_date.desc()).all()
        meds = self.db.query(PatientMedication).filter(PatientMedication.patient_id == patient.id).all()

        match_date, source, record_id = None, None, None
        hit_event = next((e for e in events if any(k in (e.event_type or "").lower() for k in keywords)), None)
        if hit_event:
            match_date, source, record_id = hit_event.event_date, "clinical_events", str(hit_event.id)
        else:
            hit_med = next((med for med in meds if any(k in med.medication_name.lower() for k in keywords)), None)
            if hit_med and (hit_med.start_date or hit_med.end_date):
                match_date = datetime.combine(hit_med.end_date or hit_med.start_date, datetime.min.time())
                source, record_id = "patient_medications", str(hit_med.id)

        if not match_date:
            return "UNKNOWN", f"No dated evidence found for '{c.criterion_text}'", {}

        elapsed = datetime.utcnow() - match_date if isinstance(match_date, datetime) else datetime.utcnow() - datetime.combine(match_date, datetime.min.time())
        within_window = elapsed <= timedelta(days=days)
        ok = within_window if direction in ("within", "before") else not within_window
        reason = f"Most recent matching evidence dated {match_date.date() if hasattr(match_date,'date') else match_date}, {elapsed.days} days ago."
        return ("MET" if ok else "NOT_MET"), reason, {"source": source, "id": record_id, "date": match_date.isoformat() if hasattr(match_date, 'isoformat') else str(match_date), "confidence": 0.85}

    def _evaluate_with_groq(self, patient: Patient, c: TrialCriterion):
        conditions = self.db.query(PatientCondition).filter(PatientCondition.patient_id == patient.id).all()
        medications = self.db.query(PatientMedication).filter(PatientMedication.patient_id == patient.id).all()
        labs = self.db.query(PatientLab).filter(PatientLab.patient_id == patient.id).order_by(PatientLab.observed_at.desc()).limit(10).all()
        events = self.db.query(ClinicalEvent).filter(ClinicalEvent.patient_id == patient.id).all()

        evidence = [
            *[{"type": "condition", "name": x.condition_name, "status": x.status, "onset_date": x.onset_date.isoformat() if x.onset_date else None} for x in conditions],
            *[{"type": "medication", "name": x.medication_name, "status": x.status, "start_date": x.start_date.isoformat() if x.start_date else None, "end_date": x.end_date.isoformat() if x.end_date else None} for x in medications],
            *[{"type": "lab", "name": x.test_name, "value": x.value_numeric, "unit": x.unit, "observed_at": x.observed_at.isoformat()} for x in labs],
            *[{"type": "clinical_event", "event_type": x.event_type, "event_date": x.event_date.isoformat() if x.event_date else None, "payload": x.payload} for x in events],
        ]
        result = self.groq.evaluate(c.criterion_text, evidence)
        decision = result.get("decision", "UNKNOWN")
        reason = result.get("reason", "No reasoning returned")
        confidence = result.get("confidence")
        return decision, reason, {"source": "groq_llm", "id": None, "confidence": confidence}
