# TrialMatchAI architecture

ClinicalTrials.gov downloaded JSON/CSV → immutable raw files → TrialProcessor → PostgreSQL → eligibility criteria → offline embeddings → pgvector candidate retrieval.

Synthea FHIR/CSV → PatientProcessor → normalized PostgreSQL tables → longitudinal timeline.

Matching (`backend/app/matching/engine.py`): structured filtering → candidate retrieval
(`GET /api/patients/{id}/candidates`, `services/semantic_retrieval.py`) → deterministic
rules (AGE/LAB/DIAGNOSIS) → temporal reasoning (`_evaluate_temporal`, reads
`TrialCriterion.temporal_constraint` against `ClinicalEvent`/`PatientMedication` dates)
→ Groq for anything still unresolved (`_evaluate_with_groq`) → evidence validation →
ranking → human review → audit. Every criterion returns MET/NOT_MET/UNKNOWN/CONFLICTING
with a cited evidence source — the engine never silently reports UNKNOWN for a category
it hasn't tried to resolve.

Monitoring: patient change → changed concept → eligibility dependency → affected criteria → affected trials → screening job → incremental re-screen → notification → audit.

Scale: PostgreSQL indexes, bulk ingestion, cursor pagination, offline embeddings, worker queues and incremental processing. The LLM never receives millions of records.
