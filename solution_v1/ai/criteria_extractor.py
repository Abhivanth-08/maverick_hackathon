import os
import json
from utils.config import GROQ_API_KEY, LLM_MODEL
from models.criteria import StructuredCriteria, CriterionNode
from utils.anonymizer import redact_pii

def extract_criteria(nct_id: str, eligibility_text: str) -> StructuredCriteria:
    if not GROQ_API_KEY:
        return StructuredCriteria(
            nct_id=nct_id,
            inclusion=[
                CriterionNode(id="INC1", type="inclusion", concept="age", operator=">=", value=18)
            ],
            exclusion=[
                CriterionNode(id="EXC1", type="exclusion", concept="pregnancy", operator="exists", value=True)
            ]
        )
    
    import groq
    client = groq.Groq(api_key=GROQ_API_KEY)
    
    # Redact PII before passing to LLM
    safe_text = redact_pii(eligibility_text[:2000])
    
    prompt = f"""Extract structured eligibility criteria from the following clinical trial text.
    Return JSON format EXACTLY matching this structure:
    {{
        "inclusion": [
            {{"id": "INC01", "type": "inclusion", "concept": "age", "operator": ">=", "value": 18, "unit": "years", "mandatory": true}}
        ],
        "exclusion": [
            {{"id": "EXC01", "type": "exclusion", "concept": "condition", "operator": "exists", "value": "pregnancy", "mandatory": true}}
        ]
    }}
    Text:
    {safe_text}
    """
    
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        inc = [CriterionNode(**item) for item in data.get('inclusion', [])]
        exc = [CriterionNode(**item) for item in data.get('exclusion', [])]
        return StructuredCriteria(nct_id=nct_id, inclusion=inc, exclusion=exc)
    except Exception as e:
        print(f"LLM Extraction failed: {e}")
        return StructuredCriteria(
            nct_id=nct_id,
            inclusion=[CriterionNode(id="INC1", type="inclusion", concept="age", operator=">=", value=18)],
            exclusion=[]
        )