# 4–5 hour demo

1. Run `alembic upgrade head`.
2. Run `python scripts/seed_demo.py`.
3. Start backend and frontend or `vercel dev`.
4. Login with `researcher@trialmatch.ai / Demo123!`.
5. Open patient P001.
6. Under "Candidate trials", click **Screen this trial** on NCT-DEMO-001 — this calls
   `POST /api/screening/{patient_id}/{trial_id}` directly from the UI.
7. Show the evidence-backed per-criterion breakdown ("Show evidence"): AGE and LAB
   resolve deterministically, TREATMENT_HISTORY resolves via the temporal engine using
   the seeded chemotherapy date, and the ECOG criterion is routed to Groq (or reports
   "GROQ_API_KEY is not configured" if no key is set, instead of silently saying UNKNOWN).
8. Click "Save anonymized note" with a note containing a name/phone number and show
   Presidio's redacted text and detected-entity count.
9. Click "Simulate new creatinine 1.8".
10. Show affected trial IDs and queued re-screening.
11. Process the queued job with `/api/jobs/{id}/process`, then re-screen and show the
    LAB criterion flip to NOT_MET.
12. Show the audit record, including the new `PATIENT_NOTE_ADDED` entries.

For a stronger presentation, explain that Synthea provides synthetic patients, ClinicalTrials.gov downloaded files provide trial data, and Groq is only used for complex natural-language criteria that the deterministic rule engine and temporal engine cannot resolve.
