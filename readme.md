# Secure EHR Insight – Clinical Validator

A zero-trust RAG prototype for querying electronic health records. A clinician picks a patient, asks a
question in chat, and the system retrieves that patient's records, strips PHI, and answers through a
guardrailed LLM.

> **Not for clinical use.** This is a research/demo project. It is not a medical device and its output
> must not be used for diagnosis or treatment decisions.

## How it works
1. **Retrieve**: the question is embedded locally (`NeuML/bioclinical-modernbert-base-embeddings`) and matched
   against the patient's rows in Postgres with pgvector.
2. **Redact**: retrieved context is passed through Microsoft Presidio (names, phones, emails, SSNs, dates,
   locations, organisations).
3. **Guard**: NeMo Guardrails blocks requests for medical advice before the LLM answers.
4. **Serve**: FastAPI (`src/api`) behind a Streamlit chat UI (`src/ui`).

## Layout
```
src/api/            FastAPI app
src/pii_redaction/  Presidio wrapper
src/guardrails/     NeMo Guardrails config and rails
src/database/       Postgres schema
src/ui/             Streamlit UI
scripts/            ingest, embed, and manual check scripts
data/               local data only (git-ignored), see data/README.md
```

## Setup
Requires Python 3.10+, PostgreSQL with the `pgvector` extension, and an OpenAI API key.

```bash
cp .env.example .env          # fill in DB_* and OPENAI_API_KEY
# obtain MIMIC-IV access and place the extract as described in data/README.md
python scripts/ingest_baseline_data.py
python scripts/apply_vector_schema.py
python scripts/generate_embeddings.py
uvicorn src.api.main:app --reload
streamlit run src/ui/app.py
```

## Data and privacy
This repository contains **no patient data**. MIMIC-IV is credentialed data governed by the PhysioNet
data use agreement and must be obtained by each user directly.

## Status
Prototype. Known gaps (authentication, tests, CI, containerisation) are tracked in the roadmap.
