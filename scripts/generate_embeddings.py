"""Generate and store clinical embeddings for rows that don't have one yet.

Resumable: each batch is committed, and only rows with a NULL embedding are processed.
"""

import argparse

from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from tqdm import tqdm

from src.config import EMBEDDING_DIM, get_settings
from src.database.engine import get_engine
from src.embeddings import build_clinical_text, vector_literal

SELECT_BATCH = text(
    """
    SELECT id, admission_type, drug, test_name, drg_severity, description, comments
    FROM patient_encounters
    WHERE clinical_embedding IS NULL
    ORDER BY id
    LIMIT :batch_size
    """
)
UPDATE_ROW = text(
    "UPDATE patient_encounters SET clinical_embedding = CAST(:embedding AS vector) WHERE id = :id"
)


def generate(model_name: str, batch_size: int, limit: int | None) -> None:
    engine = get_engine()

    print(f"Loading embedding model {model_name} ...")
    model = SentenceTransformer(model_name)
    if model.get_sentence_embedding_dimension() != EMBEDDING_DIM:
        raise ValueError(
            f"Model outputs {model.get_sentence_embedding_dimension()} dims but the database "
            f"column is vector({EMBEDDING_DIM})."
        )

    with engine.connect() as conn:
        pending = conn.execute(
            text("SELECT COUNT(*) FROM patient_encounters WHERE clinical_embedding IS NULL")
        ).scalar_one()
    total = min(pending, limit) if limit else pending
    print(f"{pending} rows need embeddings; processing {total}.")

    processed = 0
    with tqdm(total=total, desc="Embedding", unit="rows") as bar:
        while processed < total:
            size = min(batch_size, total - processed)
            with engine.begin() as conn:
                rows = conn.execute(SELECT_BATCH, {"batch_size": size}).mappings().all()
                if not rows:
                    break
                texts = [build_clinical_text(r) for r in rows]
                vectors = model.encode(texts, batch_size=batch_size)
                conn.execute(
                    UPDATE_ROW,
                    [
                        {"id": r["id"], "embedding": vector_literal(v)}
                        for r, v in zip(rows, vectors, strict=True)
                    ],
                )
            processed += len(rows)
            bar.update(len(rows))

    print(f"Done: embedded {processed} rows.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=get_settings().embedding_model)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--limit", type=int, default=None, help="max rows to embed (default: all)")
    args = parser.parse_args()
    generate(args.model, args.batch_size, args.limit)


if __name__ == "__main__":
    main()
