"""
Document Chunker Module for PromptGuard-RedLLM RAG Pipeline.

Provides structural markdown document chunking by headings and paragraphs,
followed by sliding-window token chunking.
"""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional


def chunk_document(
    text: str,
    source: str,
    max_tokens: int = 300,
    overlap: int = 40
) -> List[Dict[str, Any]]:
    """
    Split a markdown document into structured, overlapping chunks.
    
    Step 1: Structural split - split by markdown headings, then by paragraphs.
    Step 2: Any piece longer than max_tokens is split with a fixed-size sliding
            window using the given overlap.
            
    Note: We approximate tokens by words (1 token ~ 1 word).
    
    Each returned chunk is a dict:
    {"id", "text", "source", "heading", "chunk_index"}
    """
    if not text or not text.strip():
        return []

    chunks: List[Dict[str, Any]] = []
    chunk_index = 0

    # Step 1: Structural split by markdown headings
    # Matches lines starting with 1 to 6 '#' characters followed by whitespace
    heading_pattern = re.compile(r'^(#{1,6}\s+.*)$', re.MULTILINE)
    
    lines = text.splitlines()
    sections: List[tuple[str, str]] = []  # (heading_text, section_body)
    
    current_heading = ""
    current_section_lines: List[str] = []

    for line in lines:
        stripped = line.strip()
        # Check if line is a markdown heading
        if re.match(r'^#{1,6}\s+', stripped):
            # Save preceding section if it had content
            if current_section_lines:
                body = "\n".join(current_section_lines).strip()
                if body:
                    sections.append((current_heading, body))
                current_section_lines = []
            
            # Extract heading: clean stripped heading text without leading '#'
            current_heading = re.sub(r'^#{1,6}\s*', '', stripped).strip()
        else:
            current_section_lines.append(line)

    # Append the last accumulated section
    if current_section_lines:
        body = "\n".join(current_section_lines).strip()
        if body:
            sections.append((current_heading, body))

    # If no heading was found but text exists, treat entire text as one section under empty heading
    if not sections and text.strip():
        sections.append(("", text.strip()))

    # Process each heading section
    for heading, section_text in sections:
        # Split section body by paragraphs (double newlines / empty lines)
        raw_paragraphs = re.split(r'\n\s*\n', section_text)
        paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]

        for para in paragraphs:
            # Step 2: Approximate tokens by words (1 token ~ 1 word) as required by specification
            words = para.split()
            if not words:
                continue

            if len(words) <= max_tokens:
                # Piece fits within max_tokens limit
                chunk_pieces = [para]
            else:
                # Piece exceeds max_tokens: split with a fixed-size sliding window with overlap
                chunk_pieces = []
                step = max(1, max_tokens - overlap)
                start = 0
                while start < len(words):
                    end = min(len(words), start + max_tokens)
                    window_words = words[start:end]
                    chunk_pieces.append(" ".join(window_words))
                    
                    if end >= len(words):
                        break
                    start += step

            # Construct chunk dicts
            for piece_text in chunk_pieces:
                chunk_dict = {
                    "id": f"{source}_{chunk_index}",
                    "text": piece_text,
                    "source": source,
                    "heading": heading,
                    "chunk_index": chunk_index,
                }
                chunks.append(chunk_dict)
                chunk_index += 1

    return chunks


class DocumentChunker:
    """
    Object-oriented wrapper for chunking files, text strings, and directories.
    Provides backwards compatibility with earlier RAG implementations.
    """

    def __init__(self, chunk_size: int = 300, chunk_overlap: int = 40):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, text: str, source: str = "document") -> List[Dict[str, Any]]:
        """Chunk a single document string using heading/paragraph structural splitting."""
        return chunk_document(
            text=text,
            source=source,
            max_tokens=self.chunk_size,
            overlap=self.chunk_overlap
        )

    def chunk_text(self, text: str, doc_name: str = "document") -> List[Dict[str, Any]]:
        """Alias for chunk_document."""
        return self.chunk_document(text=text, source=doc_name)

    def chunk_file(self, file_path: Path | str) -> List[Dict[str, Any]]:
        """Read a file and chunk its contents."""
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            return []

        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            return []

        return self.chunk_document(text=content, source=p.name)

    def chunk_directory(self, dir_path: Path | str) -> List[Dict[str, Any]]:
        """Chunk all .md and .txt files in a directory."""
        d = Path(dir_path)
        if not d.exists() or not d.is_dir():
            return []

        all_chunks: List[Dict[str, Any]] = []
        for file in sorted(d.glob("*.*")):
            if file.suffix.lower() in [".md", ".txt", ".json"]:
                all_chunks.extend(self.chunk_file(file))

        # Re-index globally across directory
        for idx, chunk in enumerate(all_chunks):
            chunk["chunk_index"] = idx
            chunk["id"] = f"{chunk['source']}_{idx}"

        return all_chunks
