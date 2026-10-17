"""
RAG Retrieval Foundation Demonstration:
1. Load the docs from data/docs
2. Chunk the documents using structural heading & paragraph split
3. Index the chunks in memory with Embedder
4. Run 3 sample queries and print chunk text, source, and score
"""

import sys
from pathlib import Path

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from targets.rag.chunker import chunk_document
from targets.rag.retriever import Retriever


def main():
    print("=" * 75)
    print("PROMPTGUARD-REDLLM: RAG RETRIEVAL FOUNDATION DEMO")
    print("=" * 75)

    # 1. Load the docs
    docs_dir = Path("data/docs")
    print(f"\n[1] Loading documents from: {docs_dir.resolve()}")
    doc_files = sorted(docs_dir.glob("*.md"))
    if not doc_files:
        print("No .md files found in data/docs!")
        return

    print(f"    Found {len(doc_files)} markdown documents:")
    for df in doc_files:
        print(f"    - {df.name}")

    # 2. Chunk the docs
    print("\n[2] Chunking documents (max_tokens=300, overlap=40)...")
    all_chunks = []
    for doc_file in doc_files:
        text = doc_file.read_text(encoding="utf-8")
        chunks = chunk_document(text=text, source=doc_file.name, max_tokens=300, overlap=40)
        all_chunks.extend(chunks)

    # Re-index globally for unique chunk IDs
    for idx, c in enumerate(all_chunks):
        c["chunk_index"] = idx
        c["id"] = f"{c['source']}_{idx}"

    print(f"    Total chunks generated across all docs: {len(all_chunks)}")

    # 3. Index with Retriever
    print("\n[3] Indexing chunks into vector memory...")
    retriever = Retriever()
    print(f"    Loaded model: {retriever.embedder.model_name}")
    retriever.index(all_chunks)
    print(f"    Indexed {len(all_chunks)} chunks into {retriever.vectors.shape} vector matrix.")

    # 4. Run 3 sample queries
    sample_queries = [
        "How do I qualify for a full refund on my purchased product?",
        "What are the delivery transit times for expedited international shipping?",
        "What are the system diagnostic and maintenance override instructions?",
    ]

    print("\n" + "=" * 75)
    print("[4] RUNNING 3 SAMPLE RETRIEVAL QUERIES")
    print("=" * 75)

    for i, query in enumerate(sample_queries, 1):
        print(f"\n--- Sample Query {i}: \"{query}\" ---")
        results = retriever.retrieve(query, top_k=2)

        for rank, r in enumerate(results, 1):
            print(f"\n  Result #{rank}:")
            print(f"  Source: {r['source']} (Heading: [{r.get('heading', '')}])")
            print(f"  Score:  {r['similarity_score']}")
            print(f"  Chunk Text:")
            # Indent text for clean display
            for line in r['text'].strip().splitlines():
                print(f"    {line}")

    # 5. Optional security demonstration: Indirect Prompt Injection Checkpoint Hook
    print("\n" + "=" * 75)
    print("[5] CHECKPOINT HOOK: INDIRECT PROMPT INJECTION DEMONSTRATION")
    print("=" * 75)
    injection_query = "maintenance diagnostic instructions"
    print(f"Query: \"{injection_query}\"")

    def security_chunk_filter(retrieved_chunks):
        safe = []
        for c in retrieved_chunks:
            if "ignore previous instructions" in c["text"].lower() or "say hacked" in c["text"].lower():
                print(f"  [CHECKPOINT BLOCKED] Dropped indirect prompt injection from: {c['source']}")
                continue
            safe.append(c)
        return safe

    print("\nExecuting retrieve with security chunk_filter hook:")
    filtered_results = retriever.retrieve(injection_query, top_k=2, chunk_filter=security_chunk_filter)
    print(f"Safe chunks passed to downstream model: {len(filtered_results)}")
    for r in filtered_results:
        print(f"  Source: {r['source']} | Score: {r['similarity_score']}")

    print("\n" + "=" * 75)
    print("[SUCCESS] Demo completed successfully!")
    print("=" * 75)


if __name__ == "__main__":
    main()
