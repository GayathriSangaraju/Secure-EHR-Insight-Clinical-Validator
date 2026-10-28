"""Manual smoke test: semantic search over all embedded rows (needs a live DB)."""

import sys

from sentence_transformers import SentenceTransformer
from sqlalchemy import text

from src.config import get_settings
from src.database.engine import get_engine
from src.embeddings import vector_literal

DEFAULT_QUERY = "Patient presenting with severe liver disease and fluid retention needing diuretics"

SEARCH = text(
    """
    SELECT id, description, drug,
           clinical_embedding <=> CAST(:q AS vector) AS cosine_distance
    FROM patient_encounters
    WHERE clinical_embedding IS NOT NULL
    ORDER BY cosine_distance
    LIMIT 3
    """
)


def main() -> None:
    query = " ".join(sys.argv[1:]) or DEFAULT_QUERY
    model = SentenceTransformer(get_settings().embedding_model)
    vector = vector_literal(model.encode(query))
    print(f"Query: {query}\n")
    with get_engine().connect() as conn:
        for rank, row in enumerate(conn.execute(SEARCH, {"q": vector}).mappings(), 1):
            print(f"{rank}. distance={row['cosine_distance']:.4f}  id={row['id']}")
            print(f"   diagnosis: {row['description']}\n   drug: {row['drug']}")


if __name__ == "__main__":
    main()
