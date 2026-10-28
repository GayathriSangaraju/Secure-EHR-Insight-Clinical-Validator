"""Redaction tests against real Presidio (skipped unless Presidio and the spaCy model exist)."""

import pytest

pytest.importorskip("presidio_analyzer")
spacy = pytest.importorskip("spacy")
if not spacy.util.is_package("en_core_web_lg"):
    pytest.skip("spaCy model en_core_web_lg not installed", allow_module_level=True)

from src.pii_redaction.presidio_service import ClinicalPIIRedactor  # noqa: E402


@pytest.fixture(scope="module")
def redactor():
    return ClinicalPIIRedactor()


def test_redacts_direct_identifiers(redactor):
    text = "Contact Jane Doe at 415-555-0198 or jane.doe@email.com. SSN 234-00-1234."
    result = redactor.redact(text)
    for secret in ("Jane Doe", "415-555-0198", "jane.doe@email.com", "234-00-1234"):
        assert secret not in result.text
    assert result.counts["EMAIL_ADDRESS"] == 1


def test_deny_list_facility_is_redacted(redactor):
    assert "Mayo Clinic" not in redactor.redact("Transferred from Mayo Clinic.").text


def test_clinical_content_is_preserved(redactor):
    out = redactor.redact("Furosemide 40 mg IV given.").text
    assert "Furosemide" in out and "40 mg" in out


def test_empty_input(redactor):
    assert redactor.redact("").text == ""


def test_custom_deny_list_is_respected():
    custom = ClinicalPIIRedactor(deny_list=["Sahlgrenska"])
    assert "Sahlgrenska" not in custom.redact("Seen at Sahlgrenska last year.").text
