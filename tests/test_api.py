"""API tests with the ML stack and the database replaced by fakes.

Needs only fastapi, httpx and sqlalchemy. The lifespan (model loading) is not run,
because TestClient is used without a context manager.
"""

import json
import logging
from collections import Counter
from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy")

from fastapi.testclient import TestClient  # noqa: E402

from src.api import main  # noqa: E402
from src.pii_redaction.presidio_service import RedactionResult  # noqa: E402

ROWS = [
    SimpleNamespace(
        drug="Furosemide",
        dose_val_rx="40",
        dose_unit_rx="mg",
        route="IV",
        eventtype="discharge",
        test_name=None,
        comments="Patient John Doe stable",
        description="Cirrhosis",
    )
]
PATIENT = "10000032"


class FakeRedactor:
    def redact(self, text: str) -> RedactionResult:
        found = text.count("John Doe")
        return RedactionResult(
            text=text.replace("John Doe", "<PERSON>"), counts=Counter(PERSON=found)
        )


class FakeRails:
    def __init__(self, answer: str = "The last dose was 40mg IV.", error: Exception | None = None):
        self.answer, self.error, self.received = answer, error, []

    async def generate_async(self, messages):
        self.received = messages
        if self.error:
            raise self.error
        return {"content": self.answer}


class FakeEmbedder:
    def encode(self, _text):
        return SimpleNamespace(tolist=lambda: [0.1, 0.2, 0.3])


def make_client(monkeypatch, rails: FakeRails) -> TestClient:
    monkeypatch.setitem(main.middleware, "redactor", FakeRedactor())
    monkeypatch.setitem(main.middleware, "rails", rails)
    monkeypatch.setitem(main.middleware, "embedder", FakeEmbedder())
    monkeypatch.setattr(main, "retrieve_records", lambda patient_id, vector, top_k: ROWS)
    return TestClient(main.app)


def chat(client, content="What was John Doe's last dose?", history=()):
    messages = [*history, {"role": "user", "content": content}]
    return client.post("/api/v1/chat", json={"patient_id": PATIENT, "messages": messages})


def test_health(monkeypatch):
    assert make_client(monkeypatch, FakeRails()).get("/health").json() == {"status": "ok"}


def test_chat_happy_path_redacts_input_and_context(monkeypatch):
    rails = FakeRails()
    response = chat(make_client(monkeypatch, rails))

    assert response.status_code == 200
    body = response.json()
    assert body["llm_response"] == "The last dose was 40mg IV."
    assert body["grounded"] is True and body["warnings"] == []

    sent = rails.received[-1]["content"]
    assert "John Doe" not in sent  # neither the question nor the record comments
    assert sent.startswith("Clinical Context:") and "Furosemide" in sent


def test_chat_history_is_redacted_too(monkeypatch):
    rails = FakeRails()
    history = [
        {"role": "user", "content": "I'm reviewing John Doe."},
        {"role": "assistant", "content": "Understood, John Doe."},
    ]
    chat(make_client(monkeypatch, rails), history=history)
    assert all("John Doe" not in m["content"] for m in rails.received)
    assert len(rails.received) == 3


def test_ungrounded_figures_are_flagged(monkeypatch):
    rails = FakeRails(answer="The patient received 80 mg.")
    body = chat(make_client(monkeypatch, rails)).json()
    assert body["grounded"] is False
    assert "80mg" in body["warnings"][0]


def test_audit_log_contains_no_phi(monkeypatch, caplog):
    client = make_client(monkeypatch, FakeRails())
    with caplog.at_level(logging.INFO, logger="ehr.audit"):
        chat(client)
    events = [json.loads(r.message) for r in caplog.records if r.name == "ehr.audit"]
    assert events and events[-1]["outcome"] == "answered"
    assert events[-1]["redactions"]["PERSON"] >= 1
    raw = " ".join(r.message for r in caplog.records)
    assert "John Doe" not in raw and PATIENT not in raw and "Furosemide" not in raw


def test_llm_failure_returns_500_and_audits_error_type_only(monkeypatch, caplog):
    client = make_client(monkeypatch, FakeRails(error=RuntimeError("boom John Doe")))
    with caplog.at_level(logging.INFO, logger="ehr.audit"):
        response = chat(client)
    assert response.status_code == 500
    audit_text = " ".join(r.message for r in caplog.records if r.name == "ehr.audit")
    assert "RuntimeError" in audit_text and "boom" not in audit_text


@pytest.mark.parametrize(
    "payload",
    [
        {"patient_id": "abc", "messages": [{"role": "user", "content": "hi"}]},
        {"patient_id": "1; DROP TABLE patient_encounters", "messages": []},
        {"patient_id": PATIENT, "messages": []},
    ],
)
def test_invalid_requests_are_rejected(monkeypatch, payload):
    assert (
        make_client(monkeypatch, FakeRails()).post("/api/v1/chat", json=payload).status_code == 422
    )
