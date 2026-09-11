"""
vector_store.py
---------------
ChromaDB vector store operations for Hebrew RAG.
Handles collection creation, upserting chunks, and semantic search.
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings

from embedder import get_embedder


CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "../chroma_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "hebrew_rag")


class VectorStore:
    """ChromaDB-backed vector store for Hebrew documents."""
    
    def __init__(
        self,
        db_path: str = CHROMA_DB_PATH,
        collection_name: str = COLLECTION_NAME,
    ):
        self.db_path = str(Path(db_path).resolve())
        self.collection_name = collection_name
        
        print(f"[VectorStore] Initializing ChromaDB at: {self.db_path}")
        self.client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(anonymized_telemetry=False),
        )
        
        self.embedder = get_embedder()
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={
                "hnsw:space": "cosine",
                "description": "Hebrew RAG document chunks",
            },
        )
        print(f"[VectorStore] Collection '{collection_name}' ready. "
              f"Documents: {self.collection.count()}")
    
    def add_chunks(
        self,
        chunks: List[Dict[str, Any]],
        batch_size: int = 100,
    ) -> int:
        """
        Add chunks to the vector store.
        
        Args:
            chunks: List of chunk dicts with 'id', 'text', and metadata fields
            batch_size: Number of chunks to embed and insert per batch
        
        Returns:
            Number of chunks added
        """
        if not chunks:
            return 0
        
        print(f"[VectorStore] Adding {len(chunks)} chunks in batches of {batch_size}...")
        
        total_added = 0
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            ids = [c["id"] for c in batch]
            texts = [c["text"] for c in batch]
            
            # Build metadata (ChromaDB requires simple types)
            metadatas = []
            for c in batch:
                meta = {
                    "book_title": str(c.get("book_title", "")),
                    "chapter_index": int(c.get("chapter_index", 0)),
                    "chapter_title": str(c.get("chapter_title", "")),
                    "chapter_id": str(c.get("chapter_id", "")),
                    "chunk_index": int(c.get("chunk_index", 0)),
                    "global_chunk_index": int(c.get("global_chunk_index", 0)),
                }
                metadatas.append(meta)
            
            # Embed texts
            embeddings = self.embedder.embed_documents(texts, show_progress=False)
            
            # Upsert to ChromaDB
            self.collection.upsert(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            
            total_added += len(batch)
            print(f"[VectorStore] Batch {i // batch_size + 1}: Added {len(batch)} chunks "
                  f"({total_added}/{len(chunks)})")
        
        print(f"[VectorStore] Total documents in collection: {self.collection.count()}")
        return total_added
    
    def semantic_search(
        self,
        query: str,
        n_results: int = 10,
        where: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic (embedding-based) search.
        
        Returns list of results with 'text', 'metadata', 'distance', 'id'.
        """
        query_embedding = self.embedder.embed_query(query)
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, self.collection.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        
        hits = []
        if results["ids"] and results["ids"][0]:
            for doc_id, doc, meta, dist in zip(
                results["ids"][0],
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                hits.append({
                    "id": doc_id,
                    "text": doc,
                    "metadata": meta,
                    "score": 1 - dist,  # Convert distance to similarity
                    "search_type": "semantic",
                })
        
        return hits
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """Return all documents (for BM25 indexing)."""
        count = self.collection.count()
        if count == 0:
            return []
        
        results = self.collection.get(
            limit=count,
            include=["documents", "metadatas"],
        )
        
        docs = []
        for doc_id, doc, meta in zip(
            results["ids"],
            results["documents"],
            results["metadatas"],
        ):
            docs.append({
                "id": doc_id,
                "text": doc,
                "metadata": meta,
            })
        
        return docs
    
    def count(self) -> int:
        """Return number of documents in collection."""
        return self.collection.count()
    
    def clear(self) -> None:
        """Clear all documents from collection."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        print(f"[VectorStore] Collection cleared.")
    
    def get_chapters(self) -> List[Dict[str, Any]]:
        """Get unique chapter metadata."""
        docs = self.get_all_documents()
        seen = set()
        chapters = []
        for doc in docs:
            meta = doc["metadata"]
            key = (meta.get("chapter_index"), meta.get("chapter_title"))
            if key not in seen:
                seen.add(key)
                chapters.append({
                    "chapter_index": meta.get("chapter_index"),
                    "chapter_title": meta.get("chapter_title"),
                    "book_title": meta.get("book_title"),
                })
        chapters.sort(key=lambda x: x["chapter_index"])
        return chapters


# Module-level singleton
_store_instance: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create the global vector store instance."""
    global _store_instance
    if _store_instance is None:
        _store_instance = VectorStore()
    return _store_instance
