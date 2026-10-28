"""Quick data-integrity report for the patient_encounters table."""

from sqlalchemy import text

from src.database.engine import get_engine


def main() -> None:
    with get_engine().connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM patient_encounters")).scalar_one()
        print(f"Total records: {total}")
        if total == 0:
            print("Warning: table is empty. Run scripts/ingest_baseline_data.py first.")
            return

        patients = conn.execute(
            text("SELECT COUNT(DISTINCT subject_id) FROM patient_encounters")
        ).scalar_one()
        embedded = conn.execute(
            text("SELECT COUNT(*) FROM patient_encounters WHERE clinical_embedding IS NOT NULL")
        ).scalar_one()
        print(f"Distinct patients: {patients}")
        print(f"Rows with embeddings: {embedded} ({embedded / total:.1%})")

        print("\nSample rows:")
        rows = conn.execute(
            text(
                "SELECT subject_id, admission_type, drug, drg_severity "
                "FROM patient_encounters WHERE drug IS NOT NULL LIMIT 5"
            )
        )
        for r in rows:
            print(f"  {r.subject_id:<10} {r.admission_type!s:<10} {r.drug!s:<25} {r.drg_severity}")


if __name__ == "__main__":
    main()
