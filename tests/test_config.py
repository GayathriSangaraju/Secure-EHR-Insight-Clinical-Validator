import pytest

from src.config import ConfigError, Settings


def test_database_url_encodes_special_characters():
    s = Settings(db_host="db", db_name="clinical", db_user="app", db_password="p@ss:w/rd#1")
    assert s.database_url == "postgresql+psycopg://app:p%40ss%3Aw%2Frd%231@db:5432/clinical"


def test_postgres_url_takes_precedence():
    s = Settings(postgres_url="postgresql+psycopg://u:p@h/d", db_host="ignored")
    assert s.database_url == "postgresql+psycopg://u:p@h/d"


def test_missing_database_config_names_the_missing_variables():
    with pytest.raises(ConfigError) as exc:
        _ = Settings(db_host="db").database_url
    message = str(exc.value)
    assert "DB_NAME" in message and "DB_USER" in message and "DB_PASSWORD" in message
    assert "DB_HOST" not in message


def test_from_env_reads_and_parses(monkeypatch):
    monkeypatch.setenv("DB_HOST", "h")
    monkeypatch.setenv("API_BASE_URL", "http://api:9000/")
    monkeypatch.setenv("RETRIEVAL_TOP_K", "3")
    monkeypatch.setenv("REDACTION_ENTITIES", "PERSON, EMAIL_ADDRESS")
    monkeypatch.setenv("REDACTION_DENY_LIST", "")
    s = Settings.from_env()
    assert s.db_host == "h"
    assert s.api_chat_url == "http://api:9000/api/v1/chat"
    assert s.retrieval_top_k == 3
    assert s.redaction_entities == ("PERSON", "EMAIL_ADDRESS")
    assert s.redaction_deny_list == ()


def test_password_is_not_in_repr():
    s = Settings(
        db_password="hunter2",
        audit_hash_key="hunter3",
        postgres_url="postgresql://u:hunter4@h/d",
    )
    shown = repr(s)
    assert "hunter2" not in shown and "hunter3" not in shown and "hunter4" not in shown
