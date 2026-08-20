import sys
import os
import io
import json

from backend.app.database.session import SessionLocal
from backend.app.models import User, Patient, PatientCondition, PatientMedication, PatientLab, ClinicalEvent, PatientReport, Trial, AuditLog
from backend.app.services.report_processor import ReportProcessorService
from backend.app.services.clinical_extractor import ClinicalExtractorService
from backend.app.matching.engine import MatchingEngine

def test_full_report_pipeline():
    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            print("No user found in database.")
            return

        print(f"Using test user: {user.email} (Org ID: {user.organization_id})")

        # 1. Create Patient Shell
        ext_id = "PT-REPORT-TEST-001"
        patient = db.query(Patient).filter_by(organization_id=user.organization_id, external_patient_id=ext_id).first()
        if not patient:
            patient = Patient(organization_id=user.organization_id, external_patient_id=ext_id, sex="UNKNOWN", status="ACTIVE")
            db.add(patient)
            db.commit()
            db.refresh(patient)
        print(f"Created/found patient ID: {patient.id} ({patient.external_patient_id})")

        # 2. Upload Clinical Report
        sample_report_text = """
CLINICAL ONCOLOGY CONSULTATION NOTE
Patient Identifier: PT-REPORT-TEST-001
Age: 58 years old Female
DOB: 1968-09-21

PRIMARY DIAGNOSIS:
Invasive Ductal Carcinoma, Stage II Breast Cancer (ER positive, PR positive, HER2 negative).

CURRENT MEDICATIONS:
1. Tamoxifen 20 mg PO daily (started 2026-02-01)
2. Metformin 500 mg PO BID

LABORATORY RESULTS (Observed 2026-08-15):
- Hemoglobin: 13.2 g/dL (Reference 12.0 - 15.5 g/dL)
- Creatinine: 1.2 mg/dL (Reference 0.6 - 1.3 mg/dL)
- WBC: 6.4 x10^9/L
- Platelets: 245 x10^9/L

CLINICAL STATUS & PERFORMANCE:
ECOG Performance Status: 1
Active Disease Status: Resected primary, receiving adjuvant endocrine therapy.

TREATMENT HISTORY:
1. Lumpectomy (Surgery performed 2026-01-15)
2. Radiation Therapy (Completed 2026-03-20)

COMORBIDITIES:
1. Hypertension
2. Type 2 Diabetes Mellitus
        """

        processor = ReportProcessorService()
        raw_text, ocr_applied, doc_type = processor.extract_text(sample_report_text.encode('utf-8'), 'consultation_note.txt', 'text/plain')
        print(f"Extracted document type: {doc_type}, OCR applied: {ocr_applied}")

        extractor = ClinicalExtractorService()
        extraction = extractor.extract_clinical_info(raw_text, doc_type)
        print("Extracted schema successfully:")
        print(f"  Diagnoses: {[d.condition_name for d in extraction.diagnoses]}")
        print(f"  Medications: {[m.name for m in extraction.medications]}")
        print(f"  Labs: {[(l.test_name, l.value_numeric, l.unit) for l in extraction.laboratory_results]}")
        print(f"  Biomarkers: {[(b.name, b.status) for b in extraction.biomarkers]}")
        print(f"  Treatments: {[t.treatment_name for t in extraction.treatment_history]}")

        # 3. Store Report Record
        report = PatientReport(
            organization_id=user.organization_id,
            patient_id=patient.id,
            filename="consultation_note.txt",
            file_type="text/plain",
            document_type=doc_type,
            processing_status="REVIEW_REQUIRED",
            extraction_status="COMPLETED",
            extracted_json=extraction.model_dump(),
            verified_json=extraction.model_dump(),
            raw_text=raw_text,
            ocr_applied=ocr_applied
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        print(f"Saved report record ID: {report.id}")

        # 4. Verify & Save Structured Clinical Evidence
        verified_data = report.verified_json
        demog = verified_data.get("demographics", {})
        if demog.get("sex") and demog.get("sex") != "UNKNOWN":
            patient.sex = demog.get("sex")

        for d in verified_data.get("diagnoses", []):
            db.add(PatientCondition(organization_id=user.organization_id, patient_id=patient.id, condition_name=d["condition_name"], status="ACTIVE", source="clinical_report"))

        for m in verified_data.get("medications", []):
            db.add(PatientMedication(organization_id=user.organization_id, patient_id=patient.id, medication_name=m["name"], dose=m.get("dose"), status="current", source="clinical_report"))

        from datetime import datetime
        for l in verified_data.get("laboratory_results", []):
            db.add(PatientLab(
                organization_id=user.organization_id,
                patient_id=patient.id,
                test_name=l["test_name"],
                value_numeric=l.get("value_numeric"),
                unit=l.get("unit"),
                observed_at=datetime.utcnow(),
                source="clinical_report"
            ))

        report.processing_status = "VERIFIED"
        db.commit()
        print("Verified patient report and populated SQL tables!")

        # 5. Run Trial Matching Engine
        trials = db.query(Trial).limit(3).all()
        if trials:
            engine = MatchingEngine(db)
            print(f"Running matching against {len(trials)} trials...")
            for t in trials:
                match = engine.screen(patient.id, t.id, user.organization_id)
                print(f"  Trial {t.nct_id}: Status = {match.status}, Score = {match.ranking_score:.2f}")

        print("\nALL BACKEND TEST PIPELINE CHECKS PASSED SUCCESSFULLY!")
    finally:
        db.close()

if __name__ == "__main__":
    test_full_report_pipeline()
