"""
RAG Package for PromptGuard-RedLLM.

Exposes chunk_document, DocumentChunker, Embedder, cosine_similarity,
batch_cosine_similarity, Retriever, and RAGRetriever.
"""

from targets.rag.chunker import chunk_document, DocumentChunker
from targets.rag.embedder import Embedder
from targets.rag.similarity import cosine_similarity, batch_cosine_similarity
from targets.rag.retriever import Retriever, RAGRetriever

__all__ = [
    "chunk_document",
    "DocumentChunker",
    "Embedder",
    "cosine_similarity",
    "batch_cosine_similarity",
    "Retriever",
    "RAGRetriever",
]
