"""
Retriever Module for PromptGuard-RedLLM RAG Pipeline.

Implements in-memory semantic vector indexing and retrieval with cosine similarity,
featuring an explicit checkpoint hook for indirect prompt injection defenses.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Union
import numpy as np

from targets.rag.chunker import chunk_document, DocumentChunker
from targets.rag.embedder import Embedder
from targets.rag.similarity import cosine_similarity, batch_cosine_similarity


class Retriever:
    """
    Vector-based Retriever with cosine similarity search and an explicit
    indirect prompt injection inspection hook.
    """

    def __init__(
        self,
        embedder: Optional[Embedder] = None,
        chunk_filter: Optional[Callable[[List[Dict[str, Any]]], List[Dict[str, Any]]]] = None,
    ):
        """
        Initialize Retriever.
        
        Args:
            embedder: Optional pre-loaded Embedder instance. If None, initializes a new Embedder.
            chunk_filter: Optional callable hook for filtering/sanitizing chunks before return.
        """
        self.embedder = embedder if embedder is not None else Embedder()
        self.chunk_filter = chunk_filter
        self.chunks: List[Dict[str, Any]] = []
        self.vectors: Optional[np.ndarray] = None

    def index(self, chunks: List[Dict[str, Any]]):
        """
        Embed and store chunk vectors in memory.
        
        Args:
            chunks: List of chunk dictionaries containing at least a 'text' field.
        """
        self.chunks = list(chunks)
        if not self.chunks:
            self.vectors = np.empty((0, self.embedder.dim), dtype=np.float32)
            return

        texts = [chunk.get("text", "") for chunk in self.chunks]
        self.vectors = self.embedder.embed(texts)

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        chunk_filter: Optional[Callable[[List[Dict[str, Any]]], List[Dict[str, Any]]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve top-k chunks most semantically similar to the query.
        
        Args:
            query: The user or agent query string.
            top_k: Number of chunks to retrieve (default: 3).
            chunk_filter: Optional override callable hook applied to retrieved chunks
                          BEFORE they are returned.
                          
        Returns:
            List of chunk dicts with 'similarity_score' field, sorted descending by score.
        """
        if not query or not query.strip() or not self.chunks or self.vectors is None:
            return []

        if len(self.chunks) == 0 or self.vectors.shape[0] == 0:
            return []

        # 1. Embed query into dense vector
        query_vec = self.embedder.embed([query])[0]

        # 2. Vectorized batch cosine similarity against in-memory chunk matrix (no Python loops)
        similarities = batch_cosine_similarity(query_vec, self.vectors)

        # 3. Rank top-k chunks by descending similarity score
        k = min(max(1, top_k), len(self.chunks))
        top_indices = np.argsort(-similarities)[:k]

        retrieved_results: List[Dict[str, Any]] = []
        for idx in top_indices:
            score = float(similarities[idx])
            chunk_copy = dict(self.chunks[idx])
            chunk_copy["similarity_score"] = round(score, 4)
            retrieved_results.append(chunk_copy)

        # =========================================================================
        # 🛡️ INDIRECT PROMPT INJECTION CHECKPOINT HOOK
        # =========================================================================
        # This hook allows PromptGuard / security filters to inspect, sanitize,
        # or drop chunks containing indirect prompt injections before they reach
        # the model prompt or reasoning agent.
        # =========================================================================
        active_filter = chunk_filter if chunk_filter is not None else self.chunk_filter
        if active_filter is not None:
            filtered = active_filter(retrieved_results)
            if isinstance(filtered, list):
                retrieved_results = filtered

        return retrieved_results

    def format_context_for_prompt(self, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks into a standardized RAG knowledge block."""
        if not retrieved_chunks:
            return ""

        context_blocks = []
        for idx, chunk in enumerate(retrieved_chunks, 1):
            doc = chunk.get("source") or chunk.get("doc_name") or "internal_doc"
            heading = chunk.get("heading")
            heading_str = f" [{heading}]" if heading else ""
            text = chunk.get("text", "")
            context_blocks.append(f"--- Document [{idx}]: {doc}{heading_str} ---\n{text}")

        return (
            "\n[INTERNAL ENTERPRISE KNOWLEDGE RETRIEVED VIA RAG]:\n"
            + "\n\n".join(context_blocks)
            + "\n[END OF RETRIEVED KNOWLEDGE]\n"
        )


class RAGRetriever(Retriever):
    """
    Drop-in enhanced RAGRetriever for VulnerableSupportAgent and the rest of the application.
    Loads and chunks markdown/text documents from data/docs or targets/rag/documents,
    indexing them into memory with vector embeddings.
    """

    def __init__(
        self,
        documents_dir: Optional[Union[Path, str]] = None,
        embedder: Optional[Embedder] = None,
        chunk_filter: Optional[Callable[[List[Dict[str, Any]]], List[Dict[str, Any]]]] = None,
    ):
        super().__init__(embedder=embedder, chunk_filter=chunk_filter)
        
        # Locate knowledge base directory: prioritize data/docs, then targets/rag/documents
        project_root = Path(__file__).resolve().parent.parent.parent
        data_docs = project_root / "data" / "docs"
        targets_docs = Path(__file__).resolve().parent / "documents"

        if documents_dir is not None:
            self.documents_dir = Path(documents_dir)
        elif data_docs.exists() and any(data_docs.glob("*.md")):
            self.documents_dir = data_docs
        elif targets_docs.exists():
            self.documents_dir = targets_docs
        else:
            self.documents_dir = data_docs

        self.chunker = DocumentChunker(chunk_size=300, chunk_overlap=40)
        self._load_and_index()

    def _load_and_index(self):
        """Load and index all documents from the documents directory."""
        if self.documents_dir.exists():
            all_chunks = self.chunker.chunk_directory(self.documents_dir)
            if all_chunks:
                self.index(all_chunks)
