import os
import json
from utils.config import LLM_API_KEY
from models.criteria import StructuredCriteria, CriterionNode

def extract_criteria(nct_id: str, eligibility_text: str) -> StructuredCriteria:
    if not LLM_API_KEY:
        return StructuredCriteria(
            nct_id=nct_id,
            inclusion=[
                CriterionNode(id="INC1", type="inclusion", concept="age", operator=">=", value=18)
            ],
            exclusion=[
                CriterionNode(id="EXC1", type="exclusion", concept="pregnancy", operator="exists", value=True)
            ]
        )
    
    import openai
    client = openai.OpenAI(api_key=LLM_API_KEY)
    
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
    {eligibility_text[:2000]}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
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