"""
Cosine Similarity Module for PromptGuard-RedLLM RAG Pipeline.

Implements manual cosine similarity and batch vectorized similarity using NumPy,
handling zero-vector edge cases without Python loops.
"""

import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float | np.ndarray:
    """
    Compute cosine similarity between two vectors, or between a single query vector
    and a 2D matrix of chunk vectors.
    
    cosine_similarity(a, b) = (a . b) / (||a|| * ||b||)
    
    Zero-vector edge cases are handled safely:
    If either norm is zero, the returned similarity is 0.0.
    """
    arr_a = np.asarray(a, dtype=np.float32)
    arr_b = np.asarray(b, dtype=np.float32)

    # If b is a 2D matrix, delegate to vectorized batch computation
    if arr_b.ndim == 2:
        return batch_cosine_similarity(arr_a, arr_b)

    # 1D vector - 1D vector case
    vec_a = arr_a.ravel()
    vec_b = arr_b.ravel()

    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)

    # Handle zero-vector edge case
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    dot = np.dot(vec_a, vec_b)
    sim = dot / (norm_a * norm_b)
    return float(np.clip(sim, -1.0, 1.0))


def batch_cosine_similarity(query_vec: np.ndarray, doc_matrix: np.ndarray) -> np.ndarray:
    """
    Compute cosine similarity between a single query vector (D,) and a matrix
    of chunk vectors (N, D).
    
    - Implemented purely with NumPy vectorization (no Python loops).
    - Dot products are computed via matrix-vector multiplication (docs @ query).
    - Norms are computed along axis 1.
    - Zero-vector edge cases (where query norm or document norm is zero)
      are handled safely by returning 0.0 without division-by-zero warnings.
      
    Returns:
        np.ndarray of shape (N,) containing similarity scores in [-1.0, 1.0].
    """
    q = np.asarray(query_vec, dtype=np.float32).ravel()
    docs = np.asarray(doc_matrix, dtype=np.float32)

    if docs.ndim == 1:
        docs = docs.reshape(1, -1)

    num_docs = docs.shape[0]
    if num_docs == 0:
        return np.empty((0,), dtype=np.float32)

    # Query L2 norm (scalar)
    q_norm = np.linalg.norm(q)

    # Chunk vectors L2 norms (N,)
    doc_norms = np.linalg.norm(docs, axis=1)

    # Dot products (N,) computed in a single vectorized matrix-vector operation
    dots = np.dot(docs, q)

    # Denominator (N,)
    denom = q_norm * doc_norms

    # Handle zero-vector edge case: where denom is 0.0, similarity is 0.0
    with np.errstate(divide='ignore', invalid='ignore'):
        sims = np.where(denom > 0.0, dots / denom, 0.0)

    # Clean up any potential NaNs or infs
    sims = np.nan_to_num(sims, nan=0.0, posinf=0.0, neginf=0.0)
    return np.clip(sims, -1.0, 1.0).astype(np.float32)
