# Data

This folder is intentionally empty in git. **Do not commit clinical data.**

The project is built around an extract of [MIMIC-IV](https://physionet.org/content/mimiciv/),
which is credentialed data. Under the PhysioNet Credentialed Health Data Use Agreement it may not be
redistributed, including in derived extracts or public repositories.

## Getting the data
1. Complete the CITI training and sign the data use agreement on PhysioNet.
2. Download MIMIC-IV and build the joined extract with the columns defined in
   `src/database/schema.sql`.
3. Save it as `data/MIMIC_IV_Trasncript.csv` (the path `scripts/ingest_baseline_data.py` expects).

Everything under `data/` except this file and `data/sample/` is git-ignored.
