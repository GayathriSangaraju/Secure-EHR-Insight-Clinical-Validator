"""Load the MIMIC-IV extract into Postgres.

Safe to re-run: if the table already has rows the load is skipped unless --replace is given.
"""

import argparse
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src.config import get_settings
from src.database.engine import get_engine
from src.database.migrate import run_migrations

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = PROJECT_ROOT / "data" / "MIMIC_IV_Trasncript.csv"
TABLE = "patient_encounters"


def ingest(csv_path: Path, replace: bool, read_chunk: int, insert_chunk: int) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {csv_path}. See data/README.md for how to obtain MIMIC-IV."
        )

    settings = get_settings()
    engine = get_engine()
    print(f"Target DB: {settings.db_host}:{settings.db_port}/{settings.db_name}")

    run_migrations(engine)

    with engine.begin() as conn:
        existing = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE}")).scalar_one()
        if existing and not replace:
            print(f"{TABLE} already has {existing} rows; skipping (use --replace to reload).")
            return
        if existing:
            print(f"--replace given: truncating {existing} existing rows.")
            conn.execute(text(f"TRUNCATE {TABLE} RESTART IDENTITY"))

    loaded = 0
    # utf-8-sig: the MIMIC extract starts with a byte-order mark.
    for chunk in pd.read_csv(csv_path, encoding="utf-8-sig", chunksize=read_chunk):
        chunk.to_sql(TABLE, engine, if_exists="append", index=False, chunksize=insert_chunk)
        loaded += len(chunk)
        print(f"  loaded {loaded} rows", end="\r", flush=True)

    print(f"\nIngestion complete: {loaded} rows into {TABLE}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--replace", action="store_true", help="truncate the table and reload")
    parser.add_argument("--read-chunk", type=int, default=20_000)
    parser.add_argument("--insert-chunk", type=int, default=1_000)
    args = parser.parse_args()
    ingest(args.csv, args.replace, args.read_chunk, args.insert_chunk)


if __name__ == "__main__":
    main()
