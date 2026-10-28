"""Minimal, dependency-free SQL migration runner.

Migrations are numbered files in `src/database/migrations/` (e.g. `001_init.sql`),
applied in order, once each, and recorded in the `schema_migrations` table.
"""

from __future__ import annotations

import logging
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
logger = logging.getLogger(__name__)

_LOCK_ID = 727_001  # arbitrary constant for pg_advisory_xact_lock


def list_migrations(directory: Path = MIGRATIONS_DIR) -> list[Path]:
    return sorted(directory.glob("[0-9][0-9][0-9]_*.sql"), key=lambda p: p.name)


def pending_migrations(applied: set[str], directory: Path = MIGRATIONS_DIR) -> list[Path]:
    """Migration files not yet applied, in order."""
    return [p for p in list_migrations(directory) if p.stem not in applied]


def split_statements(sql: str) -> list[str]:
    """Split a migration file into statements (no procedural bodies or ';' in strings)."""
    without_comments = "\n".join(
        line for line in sql.splitlines() if not line.lstrip().startswith("--")
    )
    return [stmt.strip() for stmt in without_comments.split(";") if stmt.strip()]


def run_migrations(engine) -> list[str]:
    """Apply all pending migrations. Returns the versions applied."""
    applied_now: list[str] = []
    with engine.begin() as conn:
        conn.exec_driver_sql(f"SELECT pg_advisory_xact_lock({_LOCK_ID})")
        conn.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        applied = {row[0] for row in conn.exec_driver_sql("SELECT version FROM schema_migrations")}
        for path in pending_migrations(applied):
            logger.info("Applying migration %s", path.name)
            for statement in split_statements(path.read_text()):
                conn.exec_driver_sql(statement)
            conn.exec_driver_sql(
                "INSERT INTO schema_migrations (version) VALUES (%s)", (path.stem,)
            )
            applied_now.append(path.stem)
    return applied_now
