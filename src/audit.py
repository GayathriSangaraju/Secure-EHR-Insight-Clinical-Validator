"""PHI-safe audit logging.

Audit events record *that* something happened (pseudonymised patient, outcome,
counts), never the question, the retrieved records, or the model's answer.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import uuid
from typing import Any

logger = logging.getLogger("ehr.audit")

# Fields an audit event may carry. Anything else is dropped, so free text
# (which could contain PHI) cannot leak into the log by accident.
ALLOWED_FIELDS = frozenset(
    {
        "event",
        "request_id",
        "patient_ref",
        "outcome",
        "records_retrieved",
        "redactions",
        "grounded",
        "ungrounded_count",
        "latency_ms",
        "error_type",
    }
)


def pseudonymise(value: str, key: str) -> str:
    """Stable, non-reversible reference for an identifier (HMAC-SHA256, truncated)."""
    digest = hmac.new(key.encode(), str(value).encode(), hashlib.sha256).hexdigest()
    return digest[:16]


def new_request_id() -> str:
    return uuid.uuid4().hex


def build_event(event: str, *, patient_id: str | None = None, key: str = "", **fields: Any) -> dict:
    record: dict[str, Any] = {"event": event, "ts": round(time.time(), 3)}
    if patient_id is not None:
        record["patient_ref"] = pseudonymise(patient_id, key)
    record.update({k: v for k, v in fields.items() if k in ALLOWED_FIELDS})
    return record


def log_event(event: str, *, patient_id: str | None = None, key: str = "", **fields: Any) -> dict:
    record = build_event(event, patient_id=patient_id, key=key, **fields)
    logger.info(json.dumps(record, sort_keys=True))
    return record
