# Contributing

```bash
git clone <repo> && cd Secure-EHR-Insight-Clinical-Validator
pip install -e ".[ml,pii,data,ui,dev]"
python -m spacy download en_core_web_lg
pre-commit install           # ruff, gitleaks, large-file guard
ruff check . && ruff format --check .
pytest
```

- Keep heavy ML imports lazy so tests run without GPU/model downloads.
- Add or update a test for behaviour changes; API tests use fakes for the model and database.
- Never commit data files (only `data/sample/` is allowed) or secrets.
