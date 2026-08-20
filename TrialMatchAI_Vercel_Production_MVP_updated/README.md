# 🧬 Synapse-KG: Neuro-Symbolic Clinical Trial Screening

**Prepared for: Hexaware Mavericks Hackathon 2026**

Synapse-KG is an enterprise-grade, privacy-first clinical trial matching engine that bridges the gap between **deterministic safety** (zero AI hallucinations) and **explainable Generative AI** (GraphRAG). 

By combining an Abstract Syntax Tree (AST) rule engine with an LLM-powered Knowledge Graph, Synapse-KG evaluates patient eligibility with 100% mathematical accuracy while providing human-readable explanations for clinicians.

---

## 🏗️ Technical Architecture & Stack
* **Frontend:** React, Vite, TypeScript (Main Dashboard) + Streamlit (Hackathon Sandbox)
* **Backend:** FastAPI, SQLAlchemy (SQLite/PostgreSQL)
* **AI / NLP:** Groq (Llama-3 / OSS Models), Microsoft Presidio (PII/PHI Redaction)
* **Knowledge Graph:** NetworkX, PyVis (Interactive HTML rendering)

---

## ⚙️ Detailed End-to-End Process Workflow

Our architecture guarantees that no Patient Health Information (PHI) ever reaches an external LLM without strict local anonymization, and no clinical decision is ever made via LLM hallucination.

### Phase 1: Secure Data Ingestion & Anonymization
1. **FHIR / HL7 Ingestion:** Patient data (Labs, Conditions, Medications, Notes) is ingested into the system.
2. **Microsoft Presidio Interception:** Before any unstructured clinical text (e.g., Doctor's Notes) is processed by the AI or saved to the readable database, it is passed through **PresidioService**.
3. **Local PII Redaction:** Presidio uses advanced NLP/spaCy to locally identify and redact names, SSNs, dates, and locations. Only the scrubbed text continues through the pipeline.

### Phase 2: Trial Extraction & AST Compilation
1. **ClinicalTrials.gov Sync:** The system automatically fetches live clinical trials via the ClinicalTrials.gov API v2.
2. **Criteria Structuring:** Complex, unstructured eligibility criteria (e.g., "Must have Creatinine < 1.5 mg/dL") are parsed into distinct data structures.
3. **AST Compilation:** These structured criteria are compiled into an **Abstract Syntax Tree (AST)**. This ensures rules are evaluated mathematically (e.g., `Value < 1.5`), completely bypassing LLM hallucination risks.

### Phase 3: Patient Knowledge Graph Construction
1. **Entity Resolution:** The backend compiles the patient's structured history (Labs, Diagnoses, Medications) into a dynamic **NetworkX Graph**.
2. **Relationship Mapping:** Nodes (e.g., "Patient", "Lab: Creatinine") are connected via directed edges (e.g., "HAS_LAB", "TAKES_MEDICATION").
3. **Interactive PyVis Rendering:** The FastAPI backend dynamically generates an interactive HTML/Canvas graph representing the patient's current clinical state, which is embedded directly into the React frontend via an iframe.

### Phase 4: Deterministic Screening & Evaluation
1. **Execution Engine:** When a researcher initiates a match, the `MatchingEngine` strictly executes the AST rules against the Patient Knowledge Graph.
2. **Status Generation:** The engine yields a deterministic array of traces (`MET`, `NOT_MET`, `UNKNOWN`) based purely on available evidence.
3. **Zero Liability:** Because the decision logic is hardcoded math/logic and not Generative AI, the hospital faces zero liability for AI diagnostic hallucinations.

### Phase 5: GraphRAG Explainability
1. **Context Assembly:** While the decision was deterministic, humans need explanations. The backend aggregates the patient's Graph nodes and the AST rule traces.
2. **Groq LLM Inference:** This secure, pre-scrubbed context is sent to the **Groq API** using Llama-3.
3. **Natural Language Rationale:** The LLM acts purely as a "translator", returning a highly readable, evidence-backed paragraph explaining *why* the rules failed or passed (GraphRAG).

### Phase 6: Dynamic HL7 Simulation (The Feedback Loop)
1. **Real-time Event Hook:** In the Hackathon Demo, a researcher can simulate an incoming HL7 lab update (e.g., a new blood test).
2. **Graph Mutation:** The backend instantly mutates the NetworkX graph with the new lab value.
3. **Instant Re-Screening:** The researcher can re-run the matching engine, and the AST instantly flips the patient's eligibility status (e.g., from `ELIGIBLE` to `NOT_ELIGIBLE`), proving real-time adaptability.

---

## 🚀 How to Run the Production Prototype

### 1. Backend (FastAPI)
Open a terminal in the project root:
```bash
# Install dependencies
pip install -r requirements-ml.txt
pip install email-validator networkx pyvis

# Seed the database with Hackathon Demo Data
python scripts/seed_demo.py

# Run the server
uvicorn backend.app.main:app --reload --port 8000
```

### 2. Frontend (React)
Open a second terminal in the `/frontend` folder:
```bash
# Install dependencies
npm install

# Run the Vite Dev Server
npm run dev
```

Navigate to `http://localhost:5173`. 
* **Login:** `researcher@trialmatch.ai`
* **Password:** `Demo123!`
* Click **🚀 Hackathon Pitch** in the sidebar to access the unified end-to-end demo!
