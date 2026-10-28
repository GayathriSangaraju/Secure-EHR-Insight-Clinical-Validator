"""Central configuration, read from environment variables (and an optional .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from urllib.parse import quote_plus

DEFAULT_EMBEDDING_MODEL = "NeuML/bioclinical-modernbert-base-embeddings"
EMBEDDING_DIM = 768
DEFAULT_REDACTION_ENTITIES = (
    "PERSON",
    "PHONE_NUMBER",
    "EMAIL_ADDRESS",
    "US_SSN",
    "LOCATION",
    "ORGANIZATION",
    "DATE_TIME",
)
DEFAULT_DENY_LIST = ("Massachusetts General Hospital", "Mayo Clinic", "Cleveland Clinic")


class ConfigError(RuntimeError):
    """Raised when required configuration is missing."""


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:  # python-dotenv is optional at runtime
        return
    load_dotenv()


def _csv(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if raw is None:
        return default
    return tuple(item.strip() for item in raw.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    db_host: str | None = None
    db_port: str = "5432"
    db_name: str | None = None
    db_user: str | None = None
    db_password: str | None = field(default=None, repr=False)
    postgres_url: str | None = field(default=None, repr=False)
    api_base_url: str = "http://localhost:8000"
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    retrieval_top_k: int = 5
    redaction_entities: tuple[str, ...] = DEFAULT_REDACTION_ENTITIES
    redaction_deny_list: tuple[str, ...] = DEFAULT_DENY_LIST
    redaction_score_threshold: float = 0.4
    audit_hash_key: str = field(default="", repr=False)
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            db_host=os.getenv("DB_HOST"),
            db_port=os.getenv("DB_PORT", "5432"),
            db_name=os.getenv("DB_NAME"),
            db_user=os.getenv("DB_USER"),
            db_password=os.getenv("DB_PASSWORD"),
            postgres_url=os.getenv("POSTGRES_URL"),
            api_base_url=os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/"),
            embedding_model=os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
            retrieval_top_k=int(os.getenv("RETRIEVAL_TOP_K", "5")),
            redaction_entities=_csv("REDACTION_ENTITIES", DEFAULT_REDACTION_ENTITIES),
            redaction_deny_list=_csv("REDACTION_DENY_LIST", DEFAULT_DENY_LIST),
            redaction_score_threshold=float(os.getenv("REDACTION_SCORE_THRESHOLD", "0.4")),
            audit_hash_key=os.getenv("AUDIT_HASH_KEY", ""),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )

    @property
    def database_url(self) -> str:
        """SQLAlchemy URL (psycopg3 driver). Credentials are URL-encoded."""
        if self.postgres_url:
            return self.postgres_url
        missing = [
            name
            for name, value in (
                ("DB_HOST", self.db_host),
                ("DB_NAME", self.db_name),
                ("DB_USER", self.db_user),
                ("DB_PASSWORD", self.db_password),
            )
            if not value
        ]
        if missing:
            raise ConfigError(
                f"Database not configured: set {', '.join(missing)} (or POSTGRES_URL). "
                "See .env.example."
            )
        user = quote_plus(self.db_user or "")
        password = quote_plus(self.db_password or "")
        return (
            f"postgresql+psycopg://{user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def api_chat_url(self) -> str:
        return f"{self.api_base_url}/api/v1/chat"

    @property
    def api_patients_url(self) -> str:
        return f"{self.api_base_url}/api/v1/patients"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_dotenv()
    return Settings.from_env()
