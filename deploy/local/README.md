# Local: Docker database + local development

Everything needed to run the project on your own machine. Pick one option.
All commands run **from the repository root**, with a `.env` file there
(`cp .env.example .env`, then set `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `OPENAI_API_KEY`, `AUDIT_HASH_KEY`).

Files here: `docker-compose.yml`, `Dockerfile`, `Dockerfile.dockerignore`.

Shorthand used below (optional, saves typing; needs Docker Compose 2.24+):

```bash
export COMPOSE_FILE=deploy/local/docker-compose.yml COMPOSE_ENV_FILES=.env
# then `docker compose up -d` works from the repo root
```

Otherwise write it in full: `docker compose -f deploy/local/docker-compose.yml --env-file .env <command>`.

## Option A: everything in Docker (nothing to install but Docker)

```bash
docker compose -f deploy/local/docker-compose.yml --env-file .env up --build -d

# once: load data and embed it (sample data shown; omit --csv for the full MIMIC file in data/)
docker compose -f deploy/local/docker-compose.yml --env-file .env run --rm api \
  python scripts/ingest_baseline_data.py --csv data/sample/synthetic_encounters.csv
docker compose -f deploy/local/docker-compose.yml --env-file .env run --rm api \
  python scripts/generate_embeddings.py --limit 100
```

Open http://localhost:8501 (UI). The API is on http://localhost:8000. The first API start downloads
the embedding model; follow it with `... logs -f api`. Give Docker Desktop at least 8 GB of memory.

Services: `db` (Postgres + pgvector), `migrate` (runs once, then exits), `api`, `ui`.

## Option B: Docker database + Python on your machine

Only the database runs in Docker; the API and UI run in your virtualenv.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[ml,pii,data,ui,dev]"
python -m spacy download en_core_web_lg

# in .env use:  DB_HOST=localhost  DB_PORT=5432
docker compose -f deploy/local/docker-compose.yml --env-file .env up -d db

python scripts/migrate.py
python scripts/ingest_baseline_data.py --csv data/sample/synthetic_encounters.csv
python scripts/generate_embeddings.py --limit 100

uvicorn src.api.main:app --reload     # terminal 1  -> http://localhost:8000
streamlit run src/ui/app.py           # terminal 2  -> http://localhost:8501
```

Run `source .venv/bin/activate` in every new terminal. A `ModuleNotFoundError` almost always means
the venv isn't active.

## Option C: your own Postgres + Python on your machine

Same as Option B, but skip the `docker compose ... up -d db` line and point `.env` at your own
Postgres (it needs the `pgvector` extension: `brew install postgresql@16 pgvector` on macOS).

## Day to day

```bash
docker compose -f deploy/local/docker-compose.yml --env-file .env up -d     # start (add --build after code changes)
docker compose -f deploy/local/docker-compose.yml --env-file .env stop      # pause, keeps data
docker compose -f deploy/local/docker-compose.yml --env-file .env down      # remove containers, keeps data
docker compose -f deploy/local/docker-compose.yml --env-file .env down -v   # ALSO deletes the database
```

Data lives in the `secure-ehr_pgdata` Docker volume, so it survives restarts. The `migrate` container
re-runs on every `up` but is a no-op when the schema is current.

## Troubleshooting

- `500` from `/api/v1/chat`: the response body's `detail` names the cause. Typical causes are a
  missing `OPENAI_API_KEY`, embeddings not generated yet, or the database not migrated.
- `DB_PASSWORD` error from compose: the password must be set in `.env`, and `--env-file .env` must be
  passed (compose looks for `.env` next to the compose file otherwise).
- "No historical records found": run `generate_embeddings.py`; only embedded patients are searchable.
