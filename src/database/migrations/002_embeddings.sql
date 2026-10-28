-- pgvector support. On managed Postgres a DBA may need to create the extension first;
-- IF NOT EXISTS makes this a no-op when it is already installed.
CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE patient_encounters
    ADD COLUMN IF NOT EXISTS clinical_embedding vector(768);

-- Approximate nearest-neighbour index for unfiltered semantic search.
-- (Per-patient chat queries are served by the subject_id index above, then ranked exactly.)
CREATE INDEX IF NOT EXISTS idx_patient_encounters_embedding_hnsw
    ON patient_encounters USING hnsw (clinical_embedding vector_cosine_ops);
