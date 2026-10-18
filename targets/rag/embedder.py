"""
Embedder Module for PromptGuard-RedLLM RAG Pipeline.

Loads the sentence-transformers model 'all-MiniLM-L6-v2' once during initialization
and exposes embed(list[str]) -> np.ndarray.
"""

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

from typing import List
import numpy as np


class Embedder:
    """
    Embedder class that loads the 'all-MiniLM-L6-v2' model once and provides:
    embed(list[str]) -> np.ndarray
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._load_model()

    def _load_model(self):
        """
        Loads the SentenceTransformer model once.
        If loading fails, raises a clear RuntimeError rather than silently faking embeddings.
        """
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            if hasattr(self.model, "get_embedding_dimension"):
                self.dim = int(self.model.get_embedding_dimension())
            else:
                self.dim = int(self.model.get_sentence_embedding_dimension())
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load sentence-transformers model '{self.model_name}'. "
                f"Ensure sentence-transformers, torch, and model weights are installed and accessible: {exc}"
            ) from exc

    def embed(self, texts: List[str]) -> np.ndarray:
        """
        Embed a list of text strings into an (N, D) NumPy array.
        
        Args:
            texts: List of document or query strings.
            
        Returns:
            np.ndarray of shape (len(texts), dim) with dtype np.float32.
        """
        if not texts:
            return np.empty((0, self.dim), dtype=np.float32)

        vectors = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return np.asarray(vectors, dtype=np.float32)
