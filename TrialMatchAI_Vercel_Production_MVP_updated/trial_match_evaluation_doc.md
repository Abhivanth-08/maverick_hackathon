# CLINICAL TRIAL MATCHING EVALUATION REPORT
**Document ID:** `DOC-MATCH-000002`  
**Generated Date:** 2026-08-16T11:28:04.838820Z  
**Organization ID:** 1  

---

## 1. PATIENT CLINICAL SUMMARY
- **External Patient ID:** ADMIN-PT-101
- **Sex / Gender:** FEMALE
- **Date of Birth:** 1985-03-20
- **Active Conditions:** Breast Cancer
- **Active Medications:** Trastuzumab

### Recent Laboratory Panels
| Lab Test | Result Value | Unit | Observed Date |
| :--- | :--- | :--- | :--- |
| Serum Creatinine | 0.8 | mg/dL | 2026-08-16T11:28:01.348048 |

---

## 2. CLINICAL TRIAL TARGET
- **NCT ID:** [NCT-DEMO-001](https://clinicaltrials.gov/study/NCT-DEMO-001)
- **Brief Title:** Demo Oncology Trial
- **Official Title:** Demo Oncology Trial
- **Study Phase:** PHASE2
- **Overall Status:** RECRUITING
- **Lead Sponsor:** N/A
- **Target Conditions:** Breast Cancer

---

## 3. MATCHING ENGINE COMPARISON EVALUATION
- **Overall Eligibility Status:** **`REQUIRES_REVIEW`**
- **Match Ranking Score:** `60.0%`
- **Evidence Completeness:** `60.0%`
- **Clinical Rationale:** 3 criteria met; 0 not met; 2 unknown. Human review required for final eligibility.

### Itemized Criteria Assessment Matrix
| Decision | Criteria Rationale | Evidence Source | Confidence |
| :--- | :--- | :--- | :--- |
| **MET** | Estimated age 41.4 years; criterion threshold 18.0. | N/A | 0.0 |
| **MET** | Matching condition evidence: Breast Cancer | patient_conditions | 0.9 |
| **MET** | Latest creatinine: 0.8 mg/dL; threshold 1.5. | patient_labs | 0.98 |
| **UNKNOWN** | Insufficient information about chemotherapy administration within 30 days | groq_llm | 0.0 |
| **UNKNOWN** | No ECOG performance status information provided | groq_llm | 1.0 |

---

## 4. CLINICAL SIGN-OFF DISCLAIMER
> **NOTICE:** This report is generated automatically by TrialMatchAI using ClinicalTrials.gov v2 protocols. It serves as clinical decision support only and requires review and verification by an authorized principal investigator or qualified physician prior to patient enrollment.
