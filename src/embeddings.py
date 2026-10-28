"""Shared helpers for turning an encounter row into text for embedding."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

MAX_COMMENT_CHARS = 250


def build_clinical_text(row: Mapping[str, Any]) -> str:
    """Build the text that gets embedded for one `patient_encounters` row.

    Empty fields are skipped. A row with no usable fields still yields a
    non-empty string so the embedding job always makes progress.
    """
    parts: list[str] = []
    if row.get("admission_type"):
        parts.append(f"Admission: {row['admission_type']}")
    if row.get("drug"):
        parts.append(f"Prescribed: {row['drug']}")
    if row.get("test_name"):
        parts.append(f"Lab Test: {row['test_name']}")
    if row.get("drg_severity"):
        parts.append(f"Severity Level: {row['drg_severity']}")
    if row.get("description"):
        parts.append(f"Diagnosis: {row['description']}")
    if row.get("comments"):
        parts.append(f"Notes: {str(row['comments']).strip()[:MAX_COMMENT_CHARS]}")
    return " | ".join(parts) if parts else "Encounter record"


def vector_literal(embedding: Any) -> str:
    """Format an embedding as a pgvector literal, e.g. '[0.1,0.2]'."""
    return "[" + ",".join(f"{float(x):.8g}" for x in embedding) + "]"
