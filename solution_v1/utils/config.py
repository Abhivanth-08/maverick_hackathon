import os
from dotenv import load_dotenv

load_dotenv()

CLINICALTRIALS_API_BASE = os.getenv("CLINICALTRIALS_API_BASE", "https://clinicaltrials.gov/api/v2")
FHIR_BASE_URL = os.getenv("FHIR_BASE_URL", "http://hapi.fhir.org/baseR4")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
NLI_MODEL = os.getenv("NLI_MODEL", "openai/gpt-oss-120b")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///synapse.db")