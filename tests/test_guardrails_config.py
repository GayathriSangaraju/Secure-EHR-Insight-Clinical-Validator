"""Static consistency checks for the Colang rails and NeMo config (no LLM needed)."""

import re
from pathlib import Path

import yaml

GUARDRAILS = Path(__file__).resolve().parent.parent / "src" / "guardrails"
COLANG = (GUARDRAILS / "rails.co").read_text()


def _defined(kind: str) -> set[str]:
    return set(re.findall(rf"^define {kind} (.+)$", COLANG, flags=re.MULTILINE))


def test_every_flow_references_defined_intents_and_responses():
    users, bots = _defined("user"), _defined("bot")
    flows = re.findall(r"^define flow .+\n((?:  .+\n?)+)", COLANG, flags=re.MULTILINE)
    assert flows, "no flows defined"
    for body in flows:
        for line in (ln.strip() for ln in body.splitlines()):
            kind, _, name = line.partition(" ")
            if kind == "user":
                assert name in users, f"undefined user intent: {name}"
            elif kind == "bot":
                assert name in bots, f"undefined bot message: {name}"


def test_each_blocking_intent_has_a_flow():
    blocking = ("ask for medical advice", "attempt prompt injection", "ask about other patients")
    for intent in blocking:
        assert re.search(rf"define flow .+\n  user {intent}\n", COLANG), intent


def test_intents_have_enough_examples():
    for match in re.finditer(r"^define user (.+)\n((?:  \".*\"\n?)+)", COLANG, flags=re.MULTILINE):
        assert match.group(2).count('"') // 2 >= 4, f"too few examples for {match.group(1)}"


def test_config_yml_is_valid_and_has_main_model():
    config = yaml.safe_load((GUARDRAILS / "config.yml").read_text())
    assert any(m["type"] == "main" for m in config["models"])
    assert "Never give diagnoses" in config["instructions"][0]["content"]
