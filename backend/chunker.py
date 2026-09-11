"""
chunker.py
----------
Structure-aware chunking for Hebrew text.
Produces chunks with metadata: book, chapter, section, chunk_index.
Target: ~300 tokens per chunk with 50-token overlap.
"""

import re
from typing import List, Dict, Any, Optional


# Approximate characters per token for Hebrew (Hebrew tokens are typically shorter)
CHARS_PER_TOKEN = 4
DEFAULT_CHUNK_SIZE = 300   # tokens
DEFAULT_OVERLAP = 50       # tokens


def _split_into_sentences(text: str) -> List[str]:
    """Split Hebrew/English text into sentences."""
    # Split on sentence-ending punctuation followed by whitespace or end of string
    # Handle both Hebrew and English sentence endings
    pattern = r'(?<=[.!?״])\s+(?=[א-תA-Z"׳])|(?<=[.!?])\s+(?=[א-תA-Z])'
    sentences = re.split(pattern, text)
    
    # Also split on double newlines (paragraph breaks)
    result = []
    for sent in sentences:
        parts = sent.split("\n\n")
        result.extend(p.strip() for p in parts if p.strip())
    
    return result


def _split_into_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs by double newlines."""
    paragraphs = re.split(r"\n{2,}", text)
    return [p.strip() for p in paragraphs if p.strip()]


def _char_to_tokens(n_chars: int) -> int:
    """Approximate token count from character count."""
    return n_chars // CHARS_PER_TOKEN


def _tokens_to_chars(n_tokens: int) -> int:
    """Approximate char count from token count."""
    return n_tokens * CHARS_PER_TOKEN


def chunk_text(
    text: str,
    chunk_size_tokens: int = DEFAULT_CHUNK_SIZE,
    overlap_tokens: int = DEFAULT_OVERLAP,
) -> List[str]:
    """
    Split text into overlapping chunks of approximately chunk_size_tokens.
    Strategy:
    1. Split into paragraphs
    2. Greedily fill chunks up to chunk_size
    3. Add overlap from previous chunk
    """
    max_chars = _tokens_to_chars(chunk_size_tokens)
    overlap_chars = _tokens_to_chars(overlap_tokens)
    
    paragraphs = _split_into_paragraphs(text)
    
    if not paragraphs:
        return []
    
    chunks = []
    current_chunk = []
    current_len = 0
    
    for para in paragraphs:
        para_len = len(para)
        
        # If a single paragraph is too long, split it into sentences
        if para_len > max_chars:
            sentences = _split_into_sentences(para)
            for sent in sentences:
                sent_len = len(sent)
                if current_len + sent_len + 1 > max_chars and current_chunk:
                    # Flush current chunk
                    chunks.append(" ".join(current_chunk))
                    # Keep overlap
                    overlap_text = " ".join(current_chunk)[-overlap_chars:]
                    current_chunk = [overlap_text] if overlap_text else []
                    current_len = len(overlap_text)
                
                current_chunk.append(sent)
                current_len += sent_len + 1
        else:
            if current_len + para_len + 2 > max_chars and current_chunk:
                # Flush current chunk
                chunks.append("\n\n".join(current_chunk))
                # Keep overlap: last N chars
                last_text = "\n\n".join(current_chunk)
                overlap_text = last_text[-overlap_chars:] if len(last_text) > overlap_chars else last_text
                current_chunk = [overlap_text] if overlap_text else []
                current_len = len(overlap_text)
            
            current_chunk.append(para)
            current_len += para_len + 2
    
    # Flush remaining
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
    
    return chunks


def create_chunks_from_chapters(
    chapters: List[Dict[str, Any]],
    chunk_size_tokens: int = DEFAULT_CHUNK_SIZE,
    overlap_tokens: int = DEFAULT_OVERLAP,
) -> List[Dict[str, Any]]:
    """
    Create document chunks from extracted chapters.
    
    Returns list of chunks with metadata:
        - id: unique chunk identifier
        - text: chunk text
        - book_title: str
        - chapter_index: int
        - chapter_title: str
        - chapter_id: str
        - chunk_index: int  (within chapter)
        - total_chunks_in_chapter: int
    """
    all_chunks = []
    global_chunk_idx = 0
    
    for chapter in chapters:
        text = chapter.get("text", "")
        if not text.strip():
            continue
        
        text_chunks = chunk_text(text, chunk_size_tokens, overlap_tokens)
        
        for chunk_idx, chunk_text_content in enumerate(text_chunks):
            if not chunk_text_content.strip():
                continue
            
            chunk_id = f"chunk_{chapter['chapter_index']:04d}_{chunk_idx:04d}"
            
            all_chunks.append({
                "id": chunk_id,
                "text": chunk_text_content,
                "book_title": chapter.get("book_title", ""),
                "chapter_index": chapter.get("chapter_index", 0),
                "chapter_title": chapter.get("chapter_title", ""),
                "chapter_id": chapter.get("chapter_id", ""),
                "chunk_index": chunk_idx,
                "global_chunk_index": global_chunk_idx,
            })
            global_chunk_idx += 1
        
        # Update total_chunks_in_chapter
        chapter_chunk_count = sum(
            1 for c in all_chunks
            if c["chapter_index"] == chapter["chapter_index"]
        )
        for c in all_chunks:
            if c["chapter_index"] == chapter["chapter_index"]:
                c["total_chunks_in_chapter"] = chapter_chunk_count
    
    print(f"[Chunker] Created {len(all_chunks)} chunks from {len(chapters)} chapters")
    return all_chunks


if __name__ == "__main__":
    sample_text = """
    בתחילת הספר אנו פוגשים את הדמות הראשית.
    
    זהו פרק ראשון שמתאר את הסיפור בצורה מפורטת.
    הסיפור מתרחש בעיר ירושלים.
    
    בהמשך הפרק אנו לומדים על המניעים של הדמויות.
    """
    chunks = chunk_text(sample_text)
    print(f"Got {len(chunks)} chunks")
    for i, c in enumerate(chunks):
        print(f"  Chunk {i}: {len(c)} chars - {c[:80]}...")
