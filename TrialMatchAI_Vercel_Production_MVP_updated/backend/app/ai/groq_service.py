from backend.app.core.config import get_settings

class GroqService:
    def __init__(self): self.settings=get_settings()
    def evaluate(self, criterion: str, evidence: list[dict]) -> dict:
        if not self.settings.groq_api_key:
            return {"decision":"UNKNOWN","reason":"GROQ_API_KEY is not configured","confidence":0.0}
        try:
            from groq import Groq
            from backend.app.privacy.presidio_service import PresidioService
            client=Groq(api_key=self.settings.groq_api_key)
            
            # Use Presidio to redact PII from the evidence before sending to LLM
            presidio = PresidioService.get_instance()
            safe_evidence = str(evidence)
            is_avail, _ = presidio.is_available()
            if is_avail:
                safe_evidence = presidio.anonymize(safe_evidence)

            prompt=("You are a clinical research screening assistant, not a diagnostician. "
                    "Evaluate only the supplied eligibility criterion against the supplied evidence. "
                    "Return JSON with decision MET, NOT_MET, UNKNOWN or CONFLICTING; reason; confidence (numeric float between 0.0 and 1.0). "
                    "Never infer missing facts.\n\nCriterion: "+criterion+"\nEvidence: "+safe_evidence)
            r=client.chat.completions.create(model=self.settings.groq_model,messages=[{"role":"user","content":prompt}],temperature=0,response_format={"type":"json_object"})
            import json
            data=json.loads(r.choices[0].message.content)
            if data.get("decision") not in {"MET","NOT_MET","UNKNOWN","CONFLICTING"}: data["decision"]="UNKNOWN"
            return data
        except Exception as exc:
            return {"decision":"UNKNOWN","reason":f"LLM unavailable: {type(exc).__name__}","confidence":0.0}
