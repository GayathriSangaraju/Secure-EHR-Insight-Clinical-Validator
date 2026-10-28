import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "data" / "sample" / "synthetic_encounters.csv"
INIT_SQL = ROOT / "src" / "database" / "migrations" / "001_init.sql"


def _table_columns() -> list[str]:
    pattern = re.compile(r"^\s+(\w+) (?:BIGINT|INT|VARCHAR|TEXT|SERIAL)", re.MULTILINE)
    return [c for c in pattern.findall(INIT_SQL.read_text()) if c != "id"]


def test_sample_header_matches_table_columns():
    with SAMPLE.open(newline="") as f:
        assert next(csv.reader(f)) == _table_columns()


def test_sample_is_synthetic_and_usable():
    with SAMPLE.open(newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 20
    # IDs deliberately sit far outside the MIMIC-IV range so the two can't be confused.
    assert all(int(r["subject_id"]) >= 90_000_000 for r in rows)
    assert {r["subject_id"] for r in rows} and len({r["subject_id"] for r in rows}) >= 5
