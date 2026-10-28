"""Clinical PII/PHI redaction built on Microsoft Presidio."""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field

from src.config import DEFAULT_DENY_LIST, DEFAULT_REDACTION_ENTITIES

logger = logging.getLogger(__name__)


@dataclass
class RedactionResult:
    text: str
    counts: Counter = field(default_factory=Counter)


class ClinicalPIIRedactor:
    """Redacts PHI from text before it reaches an LLM.

    Entities, the facility deny-list and the score threshold are configurable
    (see `Settings`), so deployments are not tied to the demo defaults.
    """

    def __init__(
        self,
        entities: Iterable[str] = DEFAULT_REDACTION_ENTITIES,
        deny_list: Iterable[str] = DEFAULT_DENY_LIST,
        score_threshold: float = 0.4,
    ) -> None:
        # Imported here so the rest of the app (and its tests) work without Presidio installed.
        from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
        from presidio_anonymizer import AnonymizerEngine

        logger.info("Initialising Presidio redaction engine")
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        self.target_entities = list(entities)
        self.score_threshold = score_threshold

        # Presidio's built-in SSN recognizer validates structure strictly. Clinical text
        # often has placeholder or test SSNs, so we also catch anything shaped xxx-xx-xxxx.
        ssn_pattern = Pattern(name="catch_all_ssn", regex=r"\b\d{3}-\d{2}-\d{4}\b", score=0.9)
        self.analyzer.registry.add_recognizer(
            PatternRecognizer(supported_entity="US_SSN", patterns=[ssn_pattern])
        )

        deny = [name for name in deny_list if name]
        if deny:
            self.analyzer.registry.add_recognizer(
                PatternRecognizer(
                    supported_entity="ORGANIZATION", deny_list=deny, deny_list_score=1.0
                )
            )

    def redact(self, raw_text: str) -> RedactionResult:
        if not raw_text:
            return RedactionResult(text="")

        findings = self.analyzer.analyze(
            text=raw_text,
            entities=self.target_entities,
            language="en",
            score_threshold=self.score_threshold,
        )
        anonymized = self.anonymizer.anonymize(text=raw_text, analyzer_results=findings)
        return RedactionResult(
            text=anonymized.text, counts=Counter(f.entity_type for f in findings)
        )

    def redact_clinical_context(self, raw_text: str) -> str:
        """Backwards-compatible helper returning only the redacted text."""
        return self.redact(raw_text).text


if __name__ == "__main__":
    redactor = ClinicalPIIRedactor()
    sample = (
        "Patient John Doe (SSN: 234-00-1234) was admitted to Massachusetts General Hospital "
        "on March 15th. Wife Jane Doe: 415-555-0198, jane.doe@email.com."
    )
    print("RAW:     ", sample)
    print("REDACTED:", redactor.redact_clinical_context(sample))
