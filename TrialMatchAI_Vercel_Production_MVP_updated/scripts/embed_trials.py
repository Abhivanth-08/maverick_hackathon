import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
"""Offline embedding job. Run outside Vercel after installing requirements-ml.txt.
It writes 384-dim BGE-small vectors to PostgreSQL using pgvector.
"""
import argparse
from sqlalchemy import text
from sqlalchemy.orm import Session
from sentence_transformers import SentenceTransformer
from backend.app.database.session import engine
from backend.app.models import Trial

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--model',default='BAAI/bge-small-en-v1.5'); a=ap.parse_args()
    model=SentenceTransformer(a.model)
    with engine.begin() as conn:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
        conn.execute(text('CREATE TABLE IF NOT EXISTS trial_embeddings (trial_id INTEGER PRIMARY KEY REFERENCES trials(id) ON DELETE CASCADE, model_name TEXT NOT NULL, embedding vector(384) NOT NULL)'))
    with Session(engine) as db:
        trials=db.query(Trial).all()
        for t in trials:
            body=' '.join([t.title or '',*(t.conditions or []),*(t.interventions or []),t.eligibility_text or ''])
            v=model.encode(body,normalize_embeddings=True).tolist()
            db.execute(text('INSERT INTO trial_embeddings(trial_id,model_name,embedding) VALUES (:id,:model,:v) ON CONFLICT (trial_id) DO UPDATE SET model_name=:model, embedding=:v'),{'id':t.id,'model':a.model,'v':str(v)})
        db.commit()
    print(f'Embedded {len(trials)} trials with {a.model}')
if __name__=='__main__': main()
