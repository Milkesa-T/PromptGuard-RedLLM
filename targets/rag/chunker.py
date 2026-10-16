from typing import List, Dict, Any
from pathlib import Path

class DocumentChunker:
    """Splits documents into overlapping chunks for semantic retrieval."""
    
    def __init__(self, chunk_size: int = 350, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, doc_name: str = "document") -> List[Dict[str, Any]]:
        """Split a string of text into overlapping chunks."""
        text = text.strip()
        if not text:
            return []

        chunks = []
        start = 0
        chunk_idx = 0
        step = max(1, self.chunk_size - self.chunk_overlap)

        while start < len(text):
            end = min(len(text), start + self.chunk_size)
            chunk_content = text[start:end].strip()
            
            if chunk_content:
                chunks.append({
                    "chunk_id": f"{doc_name}_{chunk_idx}",
                    "doc_name": doc_name,
                    "text": chunk_content,
                    "start_char": start,
                    "end_char": end
                })
                chunk_idx += 1
                
            if end >= len(text):
                break
            start += step

        return chunks

    def chunk_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Read a file and chunk its content."""
        p = Path(file_path)
        if not p.exists():
            return []
        
        with open(p, "r", encoding="utf-8") as f:
            content = f.read()
            
        return self.chunk_text(content, doc_name=p.name)

    def chunk_directory(self, dir_path: Path) -> List[Dict[str, Any]]:
        """Chunk all .txt and .md files in a directory."""
        d = Path(dir_path)
        if not d.exists() or not d.is_dir():
            return []

        all_chunks = []
        for file in d.glob("*.*"):
            if file.suffix.lower() in [".txt", ".md", ".json"]:
                all_chunks.extend(self.chunk_file(file))
                
        return all_chunks
