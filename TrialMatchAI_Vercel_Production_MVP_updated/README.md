# TrialMatchAI

Production-oriented hackathon MVP for evidence-aware, temporal, change-aware clinical trial screening.

## Architecture
- React + Vite frontend
- FastAPI backend exposed as a Vercel Python Function
- PostgreSQL + pgvector (recommended hosted provider: Neon)
- Groq for complex eligibility criteria only
- Microsoft Presidio for PII detection/anonymization
- Deterministic rule engine + temporal engine + semantic candidate retrieval
- Change-impact monitoring and incremental re-screening

The design follows the supplied TrialMatchAI specification: downloaded ClinicalTrials.gov records are processed into PostgreSQL; Synthea provides synthetic longitudinal patient data; the system returns MET/NOT_MET/UNKNOWN/CONFLICTING with evidence and supports change-aware re-screening.

## Vercel deployment
Vercel can host FastAPI as Python serverless functions and can serve the React build in the same project. Use a hosted Postgres database such as Neon for production; do not put PostgreSQL inside Vercel.

1. Create a Neon Postgres database with pgvector enabled.
2. Set Vercel environment variables from `.env.example`.
3. `npm install -g vercel`
4. `vercel login`
5. `vercel --prod`

The deployed frontend and `/api/*` backend share one origin.

## Local development
Requirements: Node 20+, Python 3.12+, PostgreSQL 16+ with pgvector.

Backend:
```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

For one-origin local development matching Vercel, use `vercel dev` from the repository root.

## Database
Set `DATABASE_URL` and run:
```bash
alembic upgrade head
python scripts/seed_demo.py
```

## ClinicalTrials.gov data
This project intentionally expects downloaded JSON/CSV files under `data/raw/`; runtime does not call the ClinicalTrials.gov API. Use the official downloadable study data, preserve the raw files, and run the trial processor.

Example:
```bash
python scripts/process_trials.py --input data/raw/studies.json
```

## Synthea
Generate synthetic patients externally with Synthea, place CSV/FHIR exports under `data/raw/synthea/`, then run the patient import processor.

## Security
- Synthea is the demo patient source; no real patient data is required.
- Presidio detects/anonymizes PII; it is not encryption. `POST /api/patients/{id}/notes`
  runs every free-text note through Presidio before anything is persisted — only the
  anonymized text and detected-entity metadata are stored, never the raw input.
- Use TLS, encrypted database storage/backups, RBAC, secret management, tenant isolation and audit logs in production.
- Never commit `.env`, credentials or API keys.

## Scope note
The Vercel deployment is intentionally request/response oriented. Long-running imports and million-record jobs should be dispatched to a separate worker/queue platform in a true production environment. A Vercel cron endpoint is included as a lightweight monitoring trigger, but it should not be treated as a durable job queue.
