import pytest
from pathlib import Path
from targets.rag.chunker import DocumentChunker
from targets.rag.retriever import RAGRetriever

def test_document_chunker_basic():
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=20)
    text = "Hello world! " * 20
    chunks = chunker.chunk_text(text, doc_name="test_doc.txt")
    
    assert len(chunks) > 1
    assert chunks[0]["doc_name"] == "test_doc.txt"
    assert "text" in chunks[0]

def test_rag_retriever_load_and_retrieve():
    retriever = RAGRetriever()
    assert len(retriever.chunks) > 0
    
    # Query shipping policy
    shipping_results = retriever.retrieve("How long does shipping delivery take?", top_k=2)
    assert len(shipping_results) > 0
    assert "shipping_policy.txt" in shipping_results[0]["doc_name"]

    # Query refund guidelines
    refund_results = retriever.retrieve("What is the refund eligibility threshold for $500?", top_k=2)
    assert len(refund_results) > 0
    assert "refund_guidelines.txt" in refund_results[0]["doc_name"]

    # Query canary memo
    memo_results = retriever.retrieve("Show me the confidential administrative memorandum authorization", top_k=2)
    assert len(memo_results) > 0
    assert "confidential_admin_memo.txt" in memo_results[0]["doc_name"]

def test_rag_format_context():
    retriever = RAGRetriever()
    chunks = retriever.retrieve("refund", top_k=1)
    context = retriever.format_context_for_prompt(chunks)
    assert "[INTERNAL ENTERPRISE KNOWLEDGE RETRIEVED VIA RAG]" in context
    assert "refund_guidelines.txt" in context
