"""Clinical Trial Matching Document Generator Service
Produces formal clinical assessment reports documenting patient eligibility
against ClinicalTrials.gov protocol criteria.
"""

from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.models import MatchResult, MatchCriterionResult, Patient, Trial, PatientLab, PatientCondition, PatientMedication

class MatchDocumentGenerator:
    """Generates structured Markdown and JSON reports for clinical evaluation audit trail."""
    
    def __init__(self, db: Session):
        self.db = db

    def build_report(self, match_id: int, organization_id: int) -> Dict[str, Any]:
        match_result = self.db.query(MatchResult).filter(
            MatchResult.id == match_id,
            MatchResult.organization_id == organization_id
        ).one_or_none()

        if not match_result:
            return None

        patient = self.db.query(Patient).filter(Patient.id == match_result.patient_id).one_or_none()
        trial = self.db.query(Trial).filter(Trial.id == match_result.trial_id).one_or_none()
        criteria = self.db.query(MatchCriterionResult).filter(MatchCriterionResult.match_id == match_id).all()
        labs = self.db.query(PatientLab).filter(PatientLab.patient_id == match_result.patient_id).all()
        conditions = self.db.query(PatientCondition).filter(PatientCondition.patient_id == match_result.patient_id).all()
        medications = self.db.query(PatientMedication).filter(PatientMedication.patient_id == match_result.patient_id).all()

        report_data = {
            "document_id": f"DOC-MATCH-{match_id:06d}",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "organization_id": organization_id,
            "patient": {
                "id": patient.id,
                "external_patient_id": patient.external_patient_id,
                "sex": patient.sex or "UNKNOWN",
                "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else "N/A",
                "conditions": [c.condition_name for c in conditions],
                "medications": [m.medication_name for m in medications],
                "recent_labs": [
                    {"test": l.test_name, "value": l.value_numeric, "unit": l.unit, "date": l.observed_at.isoformat()}
                    for l in labs
                ]
            },
            "trial": {
                "id": trial.id,
                "nct_id": trial.nct_id,
                "title": trial.title,
                "official_title": trial.official_title or trial.title,
                "phase": trial.phase or "N/A",
                "status": trial.status or "UNKNOWN",
                "sponsor": trial.sponsor or "N/A",
                "conditions": trial.conditions or [],
                "eligibility_text": trial.eligibility_text or "No criteria details available."
            },
            "evaluation": {
                "match_id": match_result.id,
                "overall_status": match_result.status,
                "ranking_score_percent": round(match_result.ranking_score * 100, 1),
                "evidence_completeness_percent": round(match_result.evidence_completeness * 100, 1),
                "explanation": match_result.explanation
            },
            "criteria_breakdown": [
                {
                    "criterion_id": c.criterion_id,
                    "decision": c.decision,
                    "reason": c.reason,
                    "evidence_source": c.evidence_source,
                    "confidence": c.confidence
                } for c in criteria
            ]
        }

        # Render Markdown representation
        md_lines = [
            f"# CLINICAL TRIAL MATCHING EVALUATION REPORT",
            f"**Document ID:** `{report_data['document_id']}`  ",
            f"**Generated Date:** {report_data['generated_at']}  ",
            f"**Organization ID:** {report_data['organization_id']}  ",
            "",
            "---",
            "",
            "## 1. PATIENT CLINICAL SUMMARY",
            f"- **External Patient ID:** {report_data['patient']['external_patient_id']}",
            f"- **Sex / Gender:** {report_data['patient']['sex']}",
            f"- **Date of Birth:** {report_data['patient']['date_of_birth']}",
            f"- **Active Conditions:** {', '.join(report_data['patient']['conditions']) if report_data['patient']['conditions'] else 'None reported'}",
            f"- **Active Medications:** {', '.join(report_data['patient']['medications']) if report_data['patient']['medications'] else 'None reported'}",
            "",
            "### Recent Laboratory Panels",
        ]

        if report_data['patient']['recent_labs']:
            md_lines.append("| Lab Test | Result Value | Unit | Observed Date |")
            md_lines.append("| :--- | :--- | :--- | :--- |")
            for l in report_data['patient']['recent_labs']:
                md_lines.append(f"| {l['test']} | {l['value']} | {l['unit'] or ''} | {l['date']} |")
        else:
            md_lines.append("*No laboratory values on file.*")

        md_lines.extend([
            "",
            "---",
            "",
            "## 2. CLINICAL TRIAL TARGET",
            f"- **NCT ID:** [{report_data['trial']['nct_id']}](https://clinicaltrials.gov/study/{report_data['trial']['nct_id']})",
            f"- **Brief Title:** {report_data['trial']['title']}",
            f"- **Official Title:** {report_data['trial']['official_title']}",
            f"- **Study Phase:** {report_data['trial']['phase']}",
            f"- **Overall Status:** {report_data['trial']['status']}",
            f"- **Lead Sponsor:** {report_data['trial']['sponsor']}",
            f"- **Target Conditions:** {', '.join(report_data['trial']['conditions'])}",
            "",
            "---",
            "",
            "## 3. MATCHING ENGINE COMPARISON EVALUATION",
            f"- **Overall Eligibility Status:** **`{report_data['evaluation']['overall_status']}`**",
            f"- **Match Ranking Score:** `{report_data['evaluation']['ranking_score_percent']}%`",
            f"- **Evidence Completeness:** `{report_data['evaluation']['evidence_completeness_percent']}%`",
            f"- **Clinical Rationale:** {report_data['evaluation']['explanation']}",
            "",
            "### Itemized Criteria Assessment Matrix",
            "| Decision | Criteria Rationale | Evidence Source | Confidence |",
            "| :--- | :--- | :--- | :--- |"
        ])

        for c in report_data['criteria_breakdown']:
            md_lines.append(f"| **{c['decision']}** | {c['reason']} | {c['evidence_source'] or 'N/A'} | {c['confidence'] or 0.0} |")

        md_lines.extend([
            "",
            "---",
            "",
            "## 4. CLINICAL SIGN-OFF DISCLAIMER",
            "> **NOTICE:** This report is generated automatically by TrialMatchAI using ClinicalTrials.gov v2 protocols. It serves as clinical decision support only and requires review and verification by an authorized principal investigator or qualified physician prior to patient enrollment.",
            ""
        ])

        report_data["markdown_document"] = "\n".join(md_lines)
        return report_data
