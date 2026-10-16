import math
import re
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from targets.rag.chunker import DocumentChunker

class RAGRetriever:
    """Lightweight vector and TF-IDF similarity retriever for RAG context injection."""
    
    def __init__(self, documents_dir: Optional[Path] = None):
        if documents_dir is None:
            documents_dir = Path(__file__).resolve().parent / "documents"
        self.documents_dir = Path(documents_dir)
        self.chunker = DocumentChunker(chunk_size=350, chunk_overlap=50)
        self.chunks: List[Dict[str, Any]] = []
        self._load_and_index()

    def _tokenize(self, text: str) -> List[str]:
        """Convert text into cleaned alphanumeric tokens."""
        return re.findall(r'[a-zA-Z0-9_]+', text.lower())

    def _compute_tf(self, tokens: List[str]) -> Dict[str, float]:
        """Calculate Term Frequency for a list of tokens."""
        tf = {}
        for token in tokens:
            tf[token] = tf.get(token, 0.0) + 1.0
        total = float(len(tokens)) if tokens else 1.0
        return {k: v / total for k, v in tf.items()}

    def _load_and_index(self):
        """Load all documents from directory and chunk them."""
        if self.documents_dir.exists():
            self.chunks = self.chunker.chunk_directory(self.documents_dir)

    def retrieve(self, query: str, top_k: int = 3, threshold: float = 0.0001) -> List[Dict[str, Any]]:
        """Retrieve top-K most relevant chunks for a user query."""
        query_tokens = self._tokenize(query)
        if not query_tokens or not self.chunks:
            return []

        query_tf = self._compute_tf(query_tokens)
        scored_chunks: List[Tuple[float, Dict[str, Any]]] = []

        for chunk in self.chunks:
            chunk_tokens = self._tokenize(chunk["text"])
            chunk_tf = self._compute_tf(chunk_tokens)

            # Cosine similarity dot product over TF
            score = 0.0
            for term, q_weight in query_tf.items():
                if term in chunk_tf:
                    # Boost exact matches and rare keywords
                    boost = 2.0 if len(term) > 4 else 1.0
                    score += q_weight * chunk_tf[term] * boost

            if score > threshold:
                scored_chunks.append((score, chunk))

        # Sort descending by score
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        
        results = []
        for score, chunk in scored_chunks[:top_k]:
            item = dict(chunk)
            item["similarity_score"] = round(score, 4)
            results.append(item)
            
        return results

    def format_context_for_prompt(self, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks into a prompt injection context block."""
        if not retrieved_chunks:
            return ""

        context_blocks = []
        for idx, chunk in enumerate(retrieved_chunks, 1):
            doc = chunk.get("doc_name", "internal_doc")
            text = chunk.get("text", "")
            context_blocks.append(f"--- Document [{idx}]: {doc} ---\n{text}")

        return (
            "\n[INTERNAL ENTERPRISE KNOWLEDGE RETRIEVED VIA RAG]:\n"
            + "\n\n".join(context_blocks)
            + "\n[END OF RETRIEVED KNOWLEDGE]\n"
        )
