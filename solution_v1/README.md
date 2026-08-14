# Synapse-KG — Neuro-Symbolic Clinical Trial Intelligence Platform

AI interprets. Rules decide. Evidence proves.

## Architecture

1. **Trial Ingestion**: ClinicalTrials.gov API (v2) Integration for real-world study protocol extraction.
2. **Criteria Extraction**: Language Models are strictly confined to generating Structured AST representations of text guidelines, prohibiting LLMs from rendering clinical conclusions.
3. **Patient Data Pipeline**: Native connection to Public FHIR Servers providing real patient demographics, observations, and conditions.
4. **Knowledge Graph Ecosystem**: NetworkX powered representation of heterogeneous Patient Profiles for granular visualization.
5. **Deterministic Constraint Engine**: A pure Python logical evaluator ensuring deterministic rule application. **NO LLMs are employed for final eligibility decisions.**
6. **Audit Trail**: High-fidelity SQLite / SQLAlchemy tracking ensuring complete explainability and traceability of every condition evaluation against evidence sources.

## Getting Started

```bash
cd solution_v1
pip install -r requirements.txt
cp .env.example .env
# Optional: Set LLM_API_KEY if testing live OpenAI extraction
streamlit run app.py
```
