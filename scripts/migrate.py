"""Apply pending database migrations."""

import logging

from src.config import get_settings
from src.database.engine import get_engine
from src.database.migrate import run_migrations


def main() -> None:
    logging.basicConfig(level=get_settings().log_level, format="%(message)s")
    applied = run_migrations(get_engine())
    print(f"Applied: {', '.join(applied)}" if applied else "Database already up to date.")


if __name__ == "__main__":
    main()
