"""
models
======
Embedding + retrieval models for the candidate-ranking pipeline.
 
* ``embeddings.EmbeddingGenerator`` — wraps BAAI/bge-small-en-v1.5 from
  ``sentence-transformers``. Returns L2-normalised vectors so cosine
  similarity = inner product.
* ``faiss_index.FAISSIndex``        — FAISS IndexFlatIP wrapper with
  candidate-id bookkeeping, save/load.
 
Both classes are intentionally minimal so they can be swapped out (e.g.
e5-large, ColBERT, HNSW) without touching the calling code.
"""
 