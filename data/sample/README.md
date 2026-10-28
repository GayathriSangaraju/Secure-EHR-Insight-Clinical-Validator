# Synthetic sample data

`synthetic_encounters.csv` is **entirely fabricated**: six invented patients (IDs 90000001–90000006)
with the same 31 columns as the MIMIC-IV extract. It contains no real patient data. Names, phone
numbers and emails in the `comments` column are fake and are there to exercise the redaction layer.

Use it to try the project without MIMIC-IV access:

```bash
python scripts/ingest_baseline_data.py --csv data/sample/synthetic_encounters.csv
python scripts/generate_embeddings.py
```
