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


ACCESS_LEVEL_HIERARCHY = {
    "public": 10,
    "user": 20,
    "standard": 20,
    "internal": 30,
    "confidential": 40,
    "restricted": 50,
    "admin": 60,
}


def is_chunk_accessible_for_session(
    chunk: Dict[str, Any],
    session_access_level: Optional[str] = None
) -> bool:
    """
    Check if a knowledge chunk can be accessed by the given session access level.
    If session_access_level is None, no access-control filter is enforced.
    If chunk is marked restricted (or has restricted classification in text/source)
    and session level is lower, returns False.
    """
    if session_access_level is None:
        return True

    chunk_level = chunk.get("access_level")
    if not chunk_level:
        text_upper = chunk.get("text", "").upper()
        source_lower = chunk.get("source", "").lower()
        if "RESTRICTED ACCESS" in text_upper or "TOP SECRET" in text_upper or "restricted" in source_lower:
            chunk_level = "restricted"
        elif "CONFIDENTIAL" in text_upper or "confidential" in source_lower:
            chunk_level = "confidential"
        elif "INTERNAL" in text_upper or "internal" in source_lower:
            chunk_level = "internal"
        else:
            chunk_level = "public"

    session_rank = ACCESS_LEVEL_HIERARCHY.get(str(session_access_level).lower(), 10)
    chunk_rank = ACCESS_LEVEL_HIERARCHY.get(str(chunk_level).lower(), 10)
    return session_rank >= chunk_rank


class Retriever:
    """
    Vector-based Retriever with cosine similarity search and an explicit
    indirect prompt injection inspection hook.
    """

    def __init__(
        self,
        embedder: Optional[Embedder] = None,
        chunk_filter: Optional[Callable[[List[Dict[str, Any]]], List[Dict[str, Any]]]] = None,
        session_access_level: Optional[str] = None,
    ):
        """
        Initialize Retriever.
        
        Args:
            embedder: Optional pre-loaded Embedder instance. If None, initializes a new Embedder.
            chunk_filter: Optional callable hook for filtering/sanitizing chunks before return.
            session_access_level: Optional access level for the querying session.
        """
        self.embedder = embedder if embedder is not None else Embedder()
        self.chunk_filter = chunk_filter
        self.session_access_level = session_access_level
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
        session_access_level: Optional[str] = None,
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

        # 3. Rank chunks by descending similarity score while enforcing access-control
        effective_level = session_access_level if session_access_level is not None else self.session_access_level
        all_sorted_indices = np.argsort(-similarities)

        retrieved_results: List[Dict[str, Any]] = []
        for idx in all_sorted_indices:
            chunk_copy = dict(self.chunks[idx])
            # Content marked as restricted is never returned to a session operating at a lower access level
            if effective_level is not None and not is_chunk_accessible_for_session(chunk_copy, effective_level):
                continue
            score = float(similarities[idx])
            chunk_copy["similarity_score"] = round(score, 4)
            retrieved_results.append(chunk_copy)
            if len(retrieved_results) >= max(1, top_k):
                break

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
        session_access_level: Optional[str] = None,
    ):
        super().__init__(
            embedder=embedder,
            chunk_filter=chunk_filter,
            session_access_level=session_access_level
        )
        
        project_root = Path(__file__).resolve().parent.parent.parent
        data_docs = project_root / "data" / "docs"
        targets_docs = Path(__file__).resolve().parent / "documents"

        self.documents_dirs: List[Path] = []
        if documents_dir is not None:
            self.documents_dirs = [Path(documents_dir)]
            self.documents_dir = Path(documents_dir)
        else:
            dirs = []
            if targets_docs.exists():
                dirs.append(targets_docs)
            if data_docs.exists() and any(data_docs.glob("*.md")):
                dirs.append(data_docs)
            self.documents_dirs = dirs
            self.documents_dir = dirs[0] if dirs else targets_docs

        self.chunker = DocumentChunker(chunk_size=300, chunk_overlap=40)
        self._load_and_index()

    def _load_and_index(self):
        """Load and index all documents from the configured document directories."""
        all_chunks: List[Dict[str, Any]] = []
        for d in self.documents_dirs:
            if d.exists():
                chunks = self.chunker.chunk_directory(d)
                if chunks:
                    all_chunks.extend(chunks)
        if all_chunks:
            for idx, c in enumerate(all_chunks):
                c["chunk_index"] = idx
            self.index(all_chunks)
