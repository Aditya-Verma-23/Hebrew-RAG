"""
retriever.py
------------
Hybrid retrieval combining semantic search (ChromaDB) and BM25.
Uses Reciprocal Rank Fusion (RRF) to merge rankings.
"""

import re
from typing import List, Dict, Any, Optional, Tuple

from rank_bm25 import BM25Okapi

from vector_store import get_vector_store


# RRF constant (k=60 is standard)
RRF_K = 60


def _tokenize_hebrew(text: str) -> List[str]:
    """
    Simple tokenizer for Hebrew text.
    Splits on whitespace and punctuation, filters short tokens.
    """
    # Split on whitespace and common punctuation
    tokens = re.split(r'[\s,.\-:;!?"\'()\[\]{}|/\\]+', text)
    # Filter empty and very short tokens
    tokens = [t for t in tokens if len(t) >= 2]
    return tokens


class BM25Index:
    """BM25 index over all stored documents."""
    
    def __init__(self, documents: List[Dict[str, Any]]):
        self.documents = documents
        self.doc_ids = [d["id"] for d in documents]
        
        # Tokenize documents
        tokenized_corpus = [_tokenize_hebrew(d["text"]) for d in documents]
        
        print(f"[BM25] Building index over {len(documents)} documents...")
        self.bm25 = BM25Okapi(tokenized_corpus)
        print("[BM25] Index built.")
    
    def search(self, query: str, n_results: int = 10, where: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """BM25 search, returns top-n results, optionally filtered by 'where' metadata matching."""
        query_tokens = _tokenize_hebrew(query)
        
        if not query_tokens:
            return []
        
        scores = self.bm25.get_scores(query_tokens)
        
        # Filter indices by where clause BEFORE sorting
        if where and "book_title" in where:
            book_title = where["book_title"]
            valid_indices = [i for i, doc in enumerate(self.documents) if doc["metadata"].get("book_title") == book_title]
            # Zero out scores for non-matching documents
            for i in range(len(scores)):
                if i not in valid_indices:
                    scores[i] = -1
        
        # Get top-n indices
        top_n = min(n_results, len(self.documents))
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_n]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                doc = self.documents[idx]
                results.append({
                    "id": doc["id"],
                    "text": doc["text"],
                    "metadata": doc["metadata"],
                    "score": float(scores[idx]),
                    "search_type": "bm25",
                })
        
        return results


def reciprocal_rank_fusion(
    semantic_results: List[Dict[str, Any]],
    bm25_results: List[Dict[str, Any]],
    k: int = RRF_K,
    semantic_weight: float = 0.6,
    bm25_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    """
    Merge semantic and BM25 results using Reciprocal Rank Fusion.
    
    RRF score = sum(weight / (k + rank))
    """
    rrf_scores: Dict[str, float] = {}
    doc_map: Dict[str, Dict[str, Any]] = {}
    
    # Add semantic results
    for rank, result in enumerate(semantic_results):
        doc_id = result["id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + semantic_weight / (k + rank + 1)
        doc_map[doc_id] = result
    
    # Add BM25 results
    for rank, result in enumerate(bm25_results):
        doc_id = result["id"]
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + bm25_weight / (k + rank + 1)
        if doc_id not in doc_map:
            doc_map[doc_id] = result
    
    # Sort by RRF score
    sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
    
    results = []
    for doc_id in sorted_ids:
        doc = doc_map[doc_id].copy()
        doc["rrf_score"] = rrf_scores[doc_id]
        doc["search_type"] = "hybrid"
        results.append(doc)
    
    return results


class HybridRetriever:
    """Combines semantic and BM25 search with RRF fusion."""
    
    def __init__(self):
        self.vector_store = get_vector_store()
        self._bm25_index: Optional[BM25Index] = None
    
    def _get_bm25_index(self) -> Optional[BM25Index]:
        """Lazily build BM25 index."""
        if self._bm25_index is None:
            docs = self.vector_store.get_all_documents()
            if docs:
                self._bm25_index = BM25Index(docs)
        return self._bm25_index
    
    def invalidate_bm25(self):
        """Force BM25 index rebuild on next query."""
        self._bm25_index = None
    
    def retrieve(
        self,
        query: str,
        n_results: int = 20,
        use_hybrid: bool = True,
        where: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval: semantic + BM25 with RRF.
        
        Args:
            query: Hebrew query string
            n_results: Number of candidates to retrieve
            use_hybrid: If False, use only semantic search
        
        Returns:
            Sorted list of result dicts with text, metadata, and scores
        """
        if self.vector_store.count() == 0:
            return []
        
        # Semantic search
        semantic_results = self.vector_store.semantic_search(query, n_results=n_results, where=where)
        
        if not use_hybrid:
            return semantic_results
        
        # BM25 search
        bm25_index = self._get_bm25_index()
        if bm25_index:
            bm25_results = bm25_index.search(query, n_results=n_results, where=where)
        else:
            bm25_results = []
        
        # Fuse results
        fused = reciprocal_rank_fusion(semantic_results, bm25_results)
        
        return fused[:n_results]


# Module-level singleton
_retriever_instance: Optional[HybridRetriever] = None


def get_retriever() -> HybridRetriever:
    """Get or create the global retriever instance."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = HybridRetriever()
    return _retriever_instance
