import re

from src.database.migrate import (
    MIGRATIONS_DIR,
    list_migrations,
    pending_migrations,
    split_statements,
)


def test_pending_skips_applied_and_keeps_order(tmp_path):
    for name in ("002_b.sql", "001_a.sql", "003_c.sql", "notes.txt"):
        (tmp_path / name).write_text("select 1;")
    pending = pending_migrations({"001_a"}, tmp_path)
    assert [p.name for p in pending] == ["002_b.sql", "003_c.sql"]


def test_shipped_migrations_are_numbered_without_gaps():
    numbers = [int(p.name[:3]) for p in list_migrations()]
    assert numbers == list(range(1, len(numbers) + 1))


def test_shipped_migrations_are_idempotent():
    for path in MIGRATIONS_DIR.glob("*.sql"):
        sql = path.read_text()
        for stmt in re.findall(r"CREATE (?:TABLE|INDEX|EXTENSION)[^;]*", sql):
            assert "IF NOT EXISTS" in stmt, f"{path.name}: {stmt[:60]}"
        for stmt in re.findall(r"ADD COLUMN[^,;]*", sql):
            assert "IF NOT EXISTS" in stmt, f"{path.name}: {stmt[:60]}"


def test_split_statements_ignores_comments_and_blanks():
    sql = (
        "-- header; with semicolon\n"
        "CREATE TABLE a (id INT);\n\n"
        "-- note\n"
        "CREATE INDEX i ON a (id);\n"
    )
    assert split_statements(sql) == ["CREATE TABLE a (id INT)", "CREATE INDEX i ON a (id)"]


def test_shipped_migrations_split_into_expected_statements():
    counts = {p.stem: len(split_statements(p.read_text())) for p in list_migrations()}
    assert counts == {"001_init": 2, "002_embeddings": 3}
