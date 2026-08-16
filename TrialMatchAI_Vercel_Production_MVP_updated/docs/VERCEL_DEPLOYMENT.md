# Vercel deployment

Vercel supports FastAPI on its Python runtime and can serve a React/Next.js frontend and FastAPI API in one project. This repository uses a Vite React build plus `api/index.py` as the FastAPI entrypoint.

## 1. Postgres
Use hosted PostgreSQL. For the easiest Vercel setup, install the Neon integration from the Vercel Marketplace. Enable the `vector` extension in the database.

Set:
`DATABASE_URL=postgresql+psycopg://...`

## 2. Environment variables
Set in Vercel Project Settings → Environment Variables:
- DATABASE_URL
- GROQ_API_KEY
- GROQ_MODEL
- JWT_SECRET
- JWT_EXPIRE_MINUTES
- CORS_ORIGINS (can be your Vercel origin; same-origin requests need no CORS)
- CRON_SECRET

## 3. Deploy
```bash
npm install -g vercel
vercel login
vercel --prod
```

## 4. Initialize database
Run migrations against the hosted database from a trusted machine/CI environment:
```bash
pip install -r requirements.txt
alembic upgrade head
python scripts/seed_demo.py
```

## 5. Important production boundary
Vercel Functions are serverless request/response compute. Do not depend on a process staying alive for a queue worker. The included cron route is intentionally lightweight. For million-record imports and durable screening jobs, run `scripts/` and `backend/app/workers/` in a separate worker platform (or a managed queue/worker service) while keeping the same PostgreSQL database.

## 6. Runtime API
After deployment:
- `/` React dashboard
- `/api/health` health check
- `/api/docs` Swagger UI
- `/api/openapi.json` OpenAPI schema
