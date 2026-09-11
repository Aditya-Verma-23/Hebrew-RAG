"""
epub_extractor.py
-----------------
Extracts structured text from Hebrew EPUB files.
Returns a list of chapters with metadata and raw text content.
"""

import os
import re
import zipfile
from pathlib import Path
from typing import List, Dict, Any

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup


def _extract_text_from_html(html_content: str) -> str:
    """Parse HTML/XHTML and return clean text preserving paragraph breaks."""
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Remove script and style tags
    for tag in soup(["script", "style", "meta", "link"]):
        tag.decompose()
    
    # Extract text with paragraph separators
    paragraphs = []
    for elem in soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "div", "li"]):
        text = elem.get_text(separator=" ", strip=True)
        if text:
            paragraphs.append(text)
    
    if not paragraphs:
        # Fallback: get all text
        return soup.get_text(separator="\n", strip=True)
    
    return "\n\n".join(paragraphs)


def _get_heading(html_content: str) -> str:
    """Extract heading from HTML content."""
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in ["h1", "h2", "h3", "title"]:
        elem = soup.find(tag)
        if elem:
            text = elem.get_text(strip=True)
            if text:
                return text
    return ""


def extract_epub(epub_path: str) -> List[Dict[str, Any]]:
    """
    Extract chapters from an EPUB file.
    
    Returns:
        List of dicts with keys:
            - chapter_id: str
            - chapter_index: int
            - chapter_title: str
            - text: str
            - book_title: str
    """
    book = epub.read_epub(epub_path)
    
    # Get book title
    book_title = book.title or Path(epub_path).stem
    
    chapters = []
    chapter_index = 0
    
    # Iterate through spine (reading order)
    for item_id, linear in book.spine:
        item = book.get_item_with_id(item_id)
        if item is None:
            continue
        
        if item.get_type() != ebooklib.ITEM_DOCUMENT:
            continue
        
        try:
            html_content = item.get_content().decode("utf-8", errors="replace")
        except Exception:
            continue
        
        text = _extract_text_from_html(html_content)
        
        # Skip empty or very short items (cover pages, toc pages)
        if len(text.strip()) < 50:
            continue
        
        chapter_title = _get_heading(html_content) or f"פרק {chapter_index + 1}"
        
        chapters.append({
            "chapter_id": item.get_id(),
            "chapter_index": chapter_index,
            "chapter_title": chapter_title,
            "text": text,
            "book_title": book_title,
        })
        chapter_index += 1
    
    print(f"[EPUB Extractor] Extracted {len(chapters)} chapters from '{book_title}'")
    return chapters


if __name__ == "__main__":
    import json
    chapters = extract_epub("../data/atalefim.epub")
    for ch in chapters[:3]:
        print(f"Chapter {ch['chapter_index']}: {ch['chapter_title']}")
        print(ch['text'][:200])
        print("---")
