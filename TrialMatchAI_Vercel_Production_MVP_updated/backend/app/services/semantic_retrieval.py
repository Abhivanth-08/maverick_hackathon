"""Candidate retrieval abstraction.

Production Postgres deployments can populate `trial_embeddings` with a 384-dim
BGE-small vector and use pgvector HNSW. The MVP keeps a deterministic lexical
fallback so the application still works before the offline embedding job runs.
"""
from sqlalchemy.orm import Session
from backend.app.models import Trial

def candidate_trials(db: Session, query: str, limit: int = 10):
    terms={x.lower() for x in query.split() if len(x)>3}
    trials=db.query(Trial).filter(Trial.status.ilike('%RECRUIT%')).limit(500).all()
    scored=[]
    for t in trials:
        text=' '.join([t.title or '', *(t.conditions or []), *(t.interventions or []), t.eligibility_text or '']).lower()
        score=sum(1 for term in terms if term in text)
        scored.append((score,t))
    scored.sort(key=lambda x:x[0],reverse=True)
    return [t for score,t in scored[:limit] if score>0] or [t for _,t in scored[:limit]]
