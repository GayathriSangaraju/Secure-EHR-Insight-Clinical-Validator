"""Zero-Trust Clinical RAG API.

Run locally:  uvicorn src.api.main:app --reload
"""

from __future__ import annotations

import logging
import time
from collections import Counter
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy import text

from src import audit
from src.config import get_settings
from src.database.engine import get_engine
from src.output_checks import check_grounding, grounding_warning

logger = logging.getLogger(__name__)

# Heavy ML components (spaCy, embedding model, guardrails), loaded once at startup.
middleware: dict[str, Any] = {}


def load_components() -> dict[str, Any]:
    """Load the heavy components. Imports are local so the module imports without them."""
    from nemoguardrails import LLMRails, RailsConfig
    from sentence_transformers import SentenceTransformer

    from src.pii_redaction.presidio_service import ClinicalPIIRedactor

    settings = get_settings()
    logger.info("Loading middleware components")
    return {
        "redactor": ClinicalPIIRedactor(
            entities=settings.redaction_entities,
            deny_list=settings.redaction_deny_list,
            score_threshold=settings.redaction_score_threshold,
        ),
        "rails": LLMRails(RailsConfig.from_path("./src/guardrails")),
        "embedder": SentenceTransformer(settings.embedding_model),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=get_settings().log_level)
    middleware.update(load_components())
    logger.info("System ready")
    yield
    middleware.clear()


app = FastAPI(title="Zero-Trust Clinical RAG API", lifespan=lifespan)


# --- MODELS ---
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    patient_id: str
    messages: list[ChatMessage]

    @field_validator("patient_id")
    @classmethod
    def patient_id_is_numeric(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("patient_id must be a numeric subject_id")
        return value

    @field_validator("messages")
    @classmethod
    def has_messages(cls, value: list[ChatMessage]) -> list[ChatMessage]:
        if not value:
            raise ValueError("messages must not be empty")
        return value


class ClinicalQuery(BaseModel):
    patient_id: str
    prompt: str


# --- RETRIEVAL ---
def retrieve_records(patient_id: int, query_vector: list[float], top_k: int) -> list[Any]:
    """Top-k most similar encounter rows for one patient (pgvector cosine distance)."""
    query = text(
        """
        SELECT drug, dose_val_rx, dose_unit_rx, route, eventtype, test_name, comments, description
        FROM patient_encounters
        WHERE subject_id = :subject_id AND clinical_embedding IS NOT NULL
        ORDER BY clinical_embedding <=> CAST(:query_embedding AS vector)
        LIMIT :top_k
        """
    )
    with get_engine().connect() as conn:
        return list(
            conn.execute(
                query,
                {
                    "subject_id": patient_id,
                    "query_embedding": str(query_vector),
                    "top_k": top_k,
                },
            ).fetchall()
        )


def format_context(patient_id: str, rows: list[Any]) -> str:
    if not rows:
        return f"No historical records found for patient {patient_id}."
    lines = [
        f"Drug: {r.drug} ({r.dose_val_rx} {r.dose_unit_rx}), Route: {r.route}, "
        f"Event: {r.eventtype}, Test: {r.test_name}, Comments: {r.comments}, "
        f"Diagnosis: {r.description}"
        for r in rows
    ]
    return f"[Records for Patient ID: {patient_id}]\n" + "\n".join(lines)


# --- ENDPOINT 1: DEMO (static mock record, no database) ---
@app.post("/api/v1/clinical-query")
async def process_clinical_query(query: ClinicalQuery):
    try:
        raw_db_context = f"""
        Patient John Doe (ID: {query.patient_id}) was admitted on March 15th.
        Last recorded Furosemide dosage was 40mg IV.
        Attending physician: Dr. Gregory House, ID: 20043.
        """
        redacted = middleware["redactor"].redact(raw_db_context)
        augmented_prompt = f"Clinical Context:\n{redacted.text}\n\nUser Question: {query.prompt}"
        response = await middleware["rails"].generate_async(
            messages=[{"role": "user", "content": augmented_prompt}]
        )
        return {
            "status": "success",
            "redacted_context_used": redacted.text.strip(),
            "llm_response": response["content"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# --- ENDPOINT 2: CHAT (pgvector retrieval -> redaction -> guardrails -> answer checks) ---
@app.post("/api/v1/chat")
async def process_chat(request: ChatRequest):
    settings = get_settings()
    request_id = audit.new_request_id()
    started = time.perf_counter()
    try:
        redactor = middleware["redactor"]
        latest_question = request.messages[-1].content

        # 1. Embed the question locally and retrieve this patient's closest records.
        query_vector = middleware["embedder"].encode(latest_question).tolist()
        rows = retrieve_records(int(request.patient_id), query_vector, settings.retrieval_top_k)
        raw_context = format_context(request.patient_id, rows)

        # 2. Redact everything that will reach the LLM: the records AND the user's messages.
        redactions: Counter = Counter()
        context_result = redactor.redact(raw_context)
        redactions.update(context_result.counts)

        safe_messages = []
        for msg in request.messages:
            result = redactor.redact(msg.content)
            redactions.update(result.counts)
            safe_messages.append({"role": msg.role, "content": result.text})

        # 3. Assemble the prompt (latest turn carries the redacted context).
        safe_question = safe_messages[-1]["content"]
        safe_messages[-1]["content"] = (
            f"Clinical Context:\n{context_result.text}\n\nUser Question: {safe_question}"
        )

        # 4. Route through input guardrails and the LLM.
        response = await middleware["rails"].generate_async(messages=safe_messages)
        answer = response["content"]

        # 5. Check the answer's figures against the records it was allowed to use.
        grounding = check_grounding(answer, raw_context)
        warning = grounding_warning(grounding)

        audit.log_event(
            "chat",
            patient_id=request.patient_id,
            key=settings.audit_hash_key,
            request_id=request_id,
            outcome="answered",
            records_retrieved=len(rows),
            redactions=dict(redactions),
            grounded=grounding.grounded,
            ungrounded_count=len(grounding.ungrounded),
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
        return {
            "status": "success",
            "llm_response": answer,
            "grounded": grounding.grounded,
            "warnings": [warning] if warning else [],
        }

    except Exception as e:
        audit.log_event(
            "chat",
            patient_id=request.patient_id,
            key=settings.audit_hash_key,
            request_id=request_id,
            outcome="error",
            error_type=type(e).__name__,
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


# --- ENDPOINT 3: PATIENTS WITH EMBEDDINGS ---
@app.get("/api/v1/patients")
async def get_unique_patients():
    try:
        with get_engine().connect() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT DISTINCT subject_id
                    FROM patient_encounters
                    WHERE subject_id IS NOT NULL AND clinical_embedding IS NOT NULL
                    ORDER BY subject_id
                    """
                )
            )
            patients = [str(row[0]) for row in result]
        return {"patients": patients if patients else ["No embedded patients found"]}
    except Exception as e:
        return {"patients": [], "error": str(e)}


@app.get("/health")
async def health():
    return {"status": "ok"}
