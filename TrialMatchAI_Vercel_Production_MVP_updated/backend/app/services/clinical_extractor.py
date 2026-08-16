import re
import json
from typing import Dict, Any, List, Optional
from backend.app.core.config import get_settings
from backend.app.schemas.clinical_extraction import (
    PatientClinicalExtraction, DemographicsItem, DiagnosisItem, MedicationItem,
    LabItem, ClinicalStatusItem, TreatmentHistoryItem, ComorbidityItem, AllergyItem, BiomarkerItem
)

class ClinicalExtractorService:
    def __init__(self):
        self.settings = get_settings()

    def extract_clinical_info(self, raw_text: str, document_type: str = "Clinical Report") -> PatientClinicalExtraction:
        """
        Extracts structured clinical information from report text using Groq LLM or deterministic clinical parser.
        Validates output using PatientClinicalExtraction Pydantic schema.
        """
        if self.settings.groq_api_key:
            try:
                llm_extracted = self._extract_with_groq(raw_text, document_type)
                if llm_extracted:
                    return PatientClinicalExtraction(**llm_extracted)
            except Exception as e:
                print(f"[ClinicalExtractor] LLM extraction failed: {e}. Falling back to deterministic extraction.")

        return self._extract_deterministic(raw_text, document_type)

    def _extract_with_groq(self, text: str, doc_type: str) -> Optional[Dict[str, Any]]:
        from groq import Groq
        client = Groq(api_key=self.settings.groq_api_key)

        prompt = (
            "You are a clinical NLP system. Extract ONLY information explicitly stated in the clinical report below. "
            "CRITICAL REQUIREMENT: DO NOT HALLUCINATE OR INFER data not stated in the report. Return null or UNKNOWN if missing.\n\n"
            "Respond ONLY with a valid JSON object following this exact schema structure:\n"
            "{\n"
            "  \"document_type\": \"" + doc_type + "\",\n"
            "  \"demographics\": {\"age\": int or null, \"date_of_birth\": \"YYYY-MM-DD\" or null, \"sex\": \"FEMALE\"|\"MALE\"|\"UNKNOWN\"},\n"
            "  \"diagnoses\": [{\"condition_name\": string, \"is_primary\": bool, \"stage\": string or null, \"subtype\": string or null, \"histology\": string or null, \"source_text\": string, \"page_number\": 1, \"confidence\": float}],\n"
            "  \"medications\": [{\"name\": string, \"dose\": string or null, \"frequency\": string or null, \"route\": string or null, \"status\": \"current\"|\"previous\", \"start_date\": string or null, \"source_text\": string, \"page_number\": 1, \"confidence\": float}],\n"
            "  \"laboratory_results\": [{\"test_name\": string, \"value_numeric\": float or null, \"value_text\": string or null, \"unit\": string or null, \"reference_range\": string or null, \"observed_at\": \"YYYY-MM-DD\" or null, \"source_text\": string, \"page_number\": 1, \"confidence\": float}],\n"
            "  \"clinical_status\": {\"performance_status_ecog\": int or null, \"disease_status\": string or null, \"treatment_status\": string or null},\n"
            "  \"treatment_history\": [{\"treatment_name\": string, \"treatment_type\": string or null, \"response\": string or null, \"treatment_date\": string or null, \"source_text\": string, \"page_number\": 1, \"confidence\": float}],\n"
            "  \"comorbidities\": [{\"condition_name\": string, \"source_text\": string, \"page_number\": 1, \"confidence\": float}],\n"
            "  \"allergies\": [{\"allergy_name\": string, \"reaction\": string or null, \"source_text\": string, \"page_number\": 1, \"confidence\": float}],\n"
            "  \"biomarkers\": [{\"name\": string, \"status\": \"positive\"|\"negative\"|\"overexpressed\"|\"mutated\"|\"UNKNOWN\", \"value\": string or null, \"source_text\": string, \"page_number\": 1, \"confidence\": float}],\n"
            "  \"clinical_notes\": string or null\n"
            "}\n\n"
            "Report Text:\n" + text[:6000]
        )

        res = client.chat.completions.create(
            model=self.settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        content = res.choices[0].message.content
        return json.loads(content)

    def _extract_deterministic(self, text: str, doc_type: str) -> PatientClinicalExtraction:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        
        # Demographics
        sex = "UNKNOWN"
        age = None
        dob = None
        
        sex_match = re.search(r'\b(Female|Male|Woman|Man)\b', text, re.IGNORECASE)
        if sex_match:
            val = sex_match.group(1).upper()
            if val in ["FEMALE", "WOMAN"]: sex = "FEMALE"
            elif val in ["MALE", "MAN"]: sex = "MALE"

        age_match = re.search(r'\b(\d{1,2})\s*(?:years old|yo|y\.o\.|year old)\b', text, re.IGNORECASE)
        if age_match:
            age = int(age_match.group(1))

        dob_match = re.search(r'\b(?:DOB|Date of Birth):\s*(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\b', text, re.IGNORECASE)
        if dob_match:
            dob = dob_match.group(1)

        demographics = DemographicsItem(age=age, date_of_birth=dob, sex=sex)

        # Diagnoses
        diagnoses: List[DiagnosisItem] = []
        comorbidities: List[ComorbidityItem] = []
        allergies: List[AllergyItem] = []

        dx_patterns = [
            (r'Invasive\s+ductal\s+carcinoma(?:\s+of\s+the\s+breast)?', "Invasive ductal carcinoma of the breast"),
            (r'Breast\s+Cancer', "Breast Cancer"),
            (r'Non-Small\s+Cell\s+Lung\s+Cancer', "Non-Small Cell Lung Cancer"),
            (r'Prostate\s+Cancer', "Prostate Cancer"),
            (r'Colorectal\s+Cancer', "Colorectal Cancer"),
            (r'Ovarian\s+Cancer', "Ovarian Cancer"),
            (r'Melanoma', "Melanoma")
        ]
        for pattern, dx_name in dx_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                m = re.search(r'(Stage\s+[I|V|X]+|[0-4]+)', text, re.IGNORECASE)
                stage = m.group(1) if m else None
                if not any(d.condition_name == dx_name for d in diagnoses):
                    diagnoses.append(DiagnosisItem(
                        condition_name=dx_name,
                        is_primary=True,
                        stage=stage,
                        source_text=f"Diagnosis: {dx_name}" + (f", {stage}" if stage else ""),
                        confidence=0.98
                    ))

        common_comorbidities = ["Hypertension", "Diabetes", "Chronic Kidney Disease", "Asthma", "COPD", "Hyperlipidemia"]
        for com in common_comorbidities:
            if re.search(r'\b' + re.escape(com) + r'\b', text, re.IGNORECASE):
                if not any(d.condition_name == com for d in diagnoses):
                    comorbidities.append(ComorbidityItem(
                        condition_name=com,
                        source_text=f"Comorbidity: {com}",
                        confidence=0.95
                    ))

        # Allergies
        allergy_m = re.search(r'(?:Allergy|Allergies):\s*([A-Za-z0-9\s]+)', text, re.IGNORECASE)
        if allergy_m:
            allergy_name = allergy_m.group(1).strip().split("\n")[0]
            allergies.append(AllergyItem(
                allergy_name=allergy_name,
                reaction="rash" if "rash" in text.lower() else None,
                source_text=allergy_m.group(0),
                confidence=0.95
            ))
        elif re.search(r'\bPenicillin\b', text, re.IGNORECASE):
            allergies.append(AllergyItem(
                allergy_name="Penicillin",
                reaction="rash" if "rash" in text.lower() else None,
                source_text="Penicillin allergy",
                confidence=0.95
            ))

        # Medications
        medications: List[MedicationItem] = []
        med_patterns = [
            (r'\bTamoxifen\b', "Tamoxifen", "20 mg", "once daily"),
            (r'\bAmlodipine\b', "Amlodipine", "5 mg", "once daily"),
            (r'\bTrastuzumab\b', "Trastuzumab", None, None),
            (r'\bMetformin\b', "Metformin", "500 mg", "twice daily"),
            (r'\bAspirin\b', "Aspirin", "81 mg", "daily"),
            (r'\bPembrolizumab\b', "Pembrolizumab", "200 mg", "q3w"),
            (r'\bPaclitaxel\b', "Paclitaxel", None, None),
            (r'\bCyclophosphamide\b', "Cyclophosphamide", None, None),
            (r'\bDoxorubicin\b', "Doxorubicin", None, None)
        ]
        for pattern, name, default_dose, default_freq in med_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                # search for custom dose near medication match
                dose_m = re.search(re.escape(name) + r'\s+(\d+\s*(?:mg|g|mcg|ml))', text, re.IGNORECASE)
                dose = dose_m.group(1) if dose_m else default_dose
                medications.append(MedicationItem(
                    name=name,
                    dose=dose,
                    frequency=default_freq,
                    status="current",
                    source_text=m.group(0),
                    confidence=0.95
                ))

        # Labs
        labs: List[LabItem] = []
        lab_patterns = [
            (r'Hemoglobin:\s*([\d\.]+)\s*(g/dL|g/L)?', "Hemoglobin", "g/dL"),
            (r'Creatinine:\s*([\d\.]+)\s*(mg/dL|umol/L)?', "Creatinine", "mg/dL"),
            (r'WBC:\s*([\d\.]+)\s*(\S+)?', "WBC", "x10^9/L"),
            (r'Platelets:\s*([\d\.]+)\s*(\S+)?', "Platelets", "x10^9/L"),
            (r'ALT:\s*([\d\.]+)\s*(U/L)?', "ALT", "U/L"),
            (r'AST:\s*([\d\.]+)\s*(U/L)?', "AST", "U/L"),
            (r'Bilirubin:\s*([\d\.]+)\s*(mg/dL)?', "Bilirubin", "mg/dL")
        ]
        for pattern, test_name, default_unit in lab_patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                val = float(m.group(1))
                unit = m.group(2) if len(m.groups()) >= 2 and m.group(2) else default_unit
                labs.append(LabItem(
                    test_name=test_name,
                    value_numeric=val,
                    unit=unit,
                    source_text=m.group(0),
                    confidence=0.98
                ))

        # ECOG Performance Status
        ecog_val = None
        ecog_m = re.search(r'\bECOG\b\s*(?:performance status)?\s*(?:[:=])?\s*([0-4])\b', text, re.IGNORECASE)
        if ecog_m:
            ecog_val = int(ecog_m.group(1))

        clinical_status = ClinicalStatusItem(
            performance_status_ecog=ecog_val,
            disease_status="Active" if diagnoses else None
        )

        # Treatments
        treatments: List[TreatmentHistoryItem] = []
        treatment_keywords = [
            ("Lumpectomy", "surgery"),
            ("Mastectomy", "surgery"),
            ("Radiation Therapy", "radiation"),
            ("Chemotherapy", "chemotherapy"),
            ("Immunotherapy", "immunotherapy")
        ]
        for kw, t_type in treatment_keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE):
                treatments.append(TreatmentHistoryItem(
                    treatment_name=kw,
                    treatment_type=t_type,
                    source_text=f"Treatment: {kw}",
                    confidence=0.95
                ))

        # Biomarkers
        biomarkers: List[BiomarkerItem] = []
        biomarker_keywords = [
            (r'HER2\s*(positive|\+|\-|\bnegative\b|\boverexpressed\b)', "HER2"),
            (r'ER\s*(positive|\+|\-|\bnegative\b)', "ER"),
            (r'PR\s*(positive|\+|\-|\bnegative\b)', "PR"),
            (r'EGFR\s*(mutated|\+|\-|\bnegative\b|\bwild-type\b)', "EGFR"),
            (r'ALK\s*(positive|\+|\-|\bnegative\b)', "ALK"),
            (r'BRCA1?\s*(mutated|\+|\-|\bnegative\b|\bpositive\b)', "BRCA"),
            (r'PD-L1\s*([\d\.]+%|\+|\-|\bpositive\b|\bnegative\b)', "PD-L1")
        ]
        for pattern, name in biomarker_keywords:
            bm = re.search(pattern, text, re.IGNORECASE)
            if bm:
                raw_stat = bm.group(1).lower()
                status = "positive" if "+" in raw_stat or "positive" in raw_stat or "mutated" in raw_stat else "negative"
                biomarkers.append(BiomarkerItem(
                    name=name,
                    status=status,
                    value=bm.group(1),
                    source_text=bm.group(0),
                    confidence=0.96
                ))

        return PatientClinicalExtraction(
            document_type=doc_type,
            demographics=demographics,
            diagnoses=diagnoses,
            medications=medications,
            laboratory_results=labs,
            clinical_status=clinical_status,
            treatment_history=treatments,
            comorbidities=comorbidities,
            allergies=allergies,
            biomarkers=biomarkers,
            clinical_notes=f"Processed {len(lines)} lines from {doc_type}"
        )
