"""
ingest.py
---------
One-shot ingestion pipeline: EPUB → ChromaDB.
Run this script to index the EPUB file before starting the API.

Usage:
    python ingest.py
    python ingest.py --epub ../data/atalefim.epub --clear
"""

import os
import sys
import argparse

# Force UTF-8 output on Windows (Hebrew text requires it)
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
import time
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from epub_extractor import extract_epub
from hebrew_normalizer import normalize_hebrew
from chunker import create_chunks_from_chapters
from embedder import get_embedder
from vector_store import get_vector_store


DEFAULT_EPUB = os.getenv("EPUB_PATH", "../data/atalefim.epub")


def run_ingestion(
    epub_path: str = DEFAULT_EPUB,
    chunk_size: int = 300,
    overlap: int = 50,
    clear_existing: bool = False,
    remove_nikud: bool = True,
) -> dict:
    """
    Run the full ingestion pipeline.
    
    Steps:
    1. Extract EPUB → chapters
    2. Normalize Hebrew text
    3. Chunk into overlapping segments
    4. Embed and store in ChromaDB
    
    Returns summary dict.
    """
    start_time = time.time()
    
    epub_path = str(Path(epub_path).resolve())
    if not os.path.exists(epub_path):
        raise FileNotFoundError(f"EPUB file not found: {epub_path}")
    
    print(f"\n{'='*60}")
    print(f"  Hebrew RAG Ingestion Pipeline")
    print(f"{'='*60}")
    print(f"  EPUB: {epub_path}")
    print(f"  Chunk size: {chunk_size} tokens")
    print(f"  Overlap: {overlap} tokens")
    print(f"  Remove nikud: {remove_nikud}")
    print(f"{'='*60}\n")
    
    # Initialize components
    print("Step 0: Initializing components...")
    embedder = get_embedder()
    store = get_vector_store()
    
    if clear_existing:
        print("Clearing existing collection...")
        store.clear()
    
    # Check if already indexed
    existing_count = store.count()
    if existing_count > 0 and not clear_existing:
        print(f"⚠️  Collection already has {existing_count} documents.")
        print("   Use --clear to re-index. Skipping ingestion.")
        return {"status": "skipped", "existing_chunks": existing_count}
    
    # Step 1: Extract EPUB
    print("\nStep 1: Extracting EPUB...")
    chapters = extract_epub(epub_path)
    print(f"  ✓ Extracted {len(chapters)} chapters")
    
    # Step 2: Normalize text
    print("\nStep 2: Normalizing Hebrew text...")
    for ch in chapters:
        ch["text"] = normalize_hebrew(ch["text"], remove_nikud=remove_nikud)
        ch["chapter_title"] = normalize_hebrew(ch["chapter_title"], remove_nikud=False)
    print(f"  ✓ Normalized {len(chapters)} chapters")
    
    # Step 3: Chunk
    print("\nStep 3: Chunking text...")
    chunks = create_chunks_from_chapters(chapters, chunk_size, overlap)
    print(f"  ✓ Created {len(chunks)} chunks")
    
    if not chunks:
        print("⚠️  No chunks created. Check EPUB extraction.")
        return {"status": "error", "message": "No chunks created"}
    
    # Step 4: Embed and store
    print(f"\nStep 4: Embedding and storing {len(chunks)} chunks in ChromaDB...")
    n_added = store.add_chunks(chunks)
    
    elapsed = time.time() - start_time
    
    print(f"\n{'='*60}")
    print(f"  Ingestion Complete!")
    print(f"{'='*60}")
    print(f"  Chapters extracted: {len(chapters)}")
    print(f"  Chunks created: {len(chunks)}")
    print(f"  Chunks stored: {n_added}")
    print(f"  Time elapsed: {elapsed:.1f}s")
    print(f"{'='*60}\n")
    
    return {
        "status": "success",
        "chapters": len(chapters),
        "chunks_created": len(chunks),
        "chunks_stored": n_added,
        "elapsed_seconds": round(elapsed, 1),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hebrew RAG Ingestion Pipeline")
    parser.add_argument(
        "--epub",
        default=DEFAULT_EPUB,
        help=f"Path to EPUB file (default: {DEFAULT_EPUB})",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=300,
        help="Target chunk size in tokens (default: 300)",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=50,
        help="Overlap between chunks in tokens (default: 50)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing collection before ingestion",
    )
    parser.add_argument(
        "--keep-nikud",
        action="store_true",
        help="Keep nikud (Hebrew diacritical marks) in text",
    )
    
    args = parser.parse_args()
    
    result = run_ingestion(
        epub_path=args.epub,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        clear_existing=args.clear,
        remove_nikud=not args.keep_nikud,
    )
    
    if result["status"] == "success":
        print("✅ Ingestion completed successfully!")
        sys.exit(0)
    elif result["status"] == "skipped":
        print("ℹ️  Ingestion skipped (already indexed).")
        sys.exit(0)
    else:
        print(f"❌ Ingestion failed: {result.get('message', 'Unknown error')}")
        sys.exit(1)
