import json
import logging

from src import audit


def test_pseudonymise_is_stable_and_keyed():
    a = audit.pseudonymise("10000032", "key-1")
    assert a == audit.pseudonymise("10000032", "key-1")
    assert a != audit.pseudonymise("10000032", "key-2")
    assert a != audit.pseudonymise("10000033", "key-1")
    assert "10000032" not in a


def test_event_drops_unknown_fields_so_free_text_cannot_leak():
    event = audit.build_event(
        "chat",
        patient_id="10000032",
        key="k",
        outcome="answered",
        question="What is John Doe's SSN?",
        llm_response="234-00-1234",
    )
    assert event["outcome"] == "answered"
    assert "question" not in event and "llm_response" not in event
    assert "patient_id" not in event and event["patient_ref"] != "10000032"


def test_log_event_emits_json(caplog):
    with caplog.at_level(logging.INFO, logger="ehr.audit"):
        audit.log_event("chat", patient_id="1", key="k", outcome="answered", records_retrieved=5)
    payload = json.loads(caplog.records[-1].message)
    assert payload["event"] == "chat" and payload["records_retrieved"] == 5
