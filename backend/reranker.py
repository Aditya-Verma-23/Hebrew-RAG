"""
reranker.py
-----------
Cross-encoder reranking of retrieved chunks.
Uses a multilingual cross-encoder model to rerank top candidates.
Falls back to score-based ordering if cross-encoder is unavailable.
"""

import os
from typing import List, Dict, Any, Optional

try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False


# Multilingual cross-encoder model
# mmarco-mMiniLMv2-L12-H384-v1 supports Hebrew queries
RERANKER_MODEL = os.getenv(
    "RERANKER_MODEL",
    "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
)


class Reranker:
    """Cross-encoder reranker for multilingual document reranking."""
    
    def __init__(self, model_name: str = RERANKER_MODEL):
        self.model_name = model_name
        self.model: Optional[CrossEncoder] = None
        
        if CROSS_ENCODER_AVAILABLE:
            try:
                print(f"[Reranker] Loading cross-encoder: {model_name}")
                self.model = CrossEncoder(model_name, max_length=512)
                print("[Reranker] Cross-encoder loaded.")
            except Exception as e:
                print(f"[Reranker] Warning: Could not load cross-encoder: {e}")
                print("[Reranker] Falling back to score-based reranking.")
                self.model = None
        else:
            print("[Reranker] sentence-transformers not available. Using score-based fallback.")
    
    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Rerank candidates given a query.
        
        Args:
            query: The search query
            candidates: List of candidate dicts (must have 'text' key)
            top_k: Number of results to return
        
        Returns:
            Top-k reranked results with 'rerank_score' field added
        """
        if not candidates:
            return []
        
        top_k = min(top_k, len(candidates))
        
        if self.model is None:
            # Fallback: return top-k by existing score
            sorted_candidates = sorted(
                candidates,
                key=lambda x: x.get("rrf_score", x.get("score", 0)),
                reverse=True,
            )
            for c in sorted_candidates:
                c["rerank_score"] = c.get("rrf_score", c.get("score", 0))
            return sorted_candidates[:top_k]
        
        # Build query-document pairs
        pairs = [[query, c["text"]] for c in candidates]
        
        try:
            # Score all pairs
            scores = self.model.predict(pairs, show_progress_bar=False)
            
            # Attach rerank scores
            for candidate, score in zip(candidates, scores):
                candidate["rerank_score"] = float(score)
            
            # Sort by rerank score
            reranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)
            
            return reranked[:top_k]
        
        except Exception as e:
            print(f"[Reranker] Error during reranking: {e}. Using fallback.")
            sorted_candidates = sorted(
                candidates,
                key=lambda x: x.get("rrf_score", x.get("score", 0)),
                reverse=True,
            )
            for c in sorted_candidates:
                c["rerank_score"] = c.get("rrf_score", c.get("score", 0))
            return sorted_candidates[:top_k]


# Module-level singleton
_reranker_instance: Optional[Reranker] = None


def get_reranker() -> Reranker:
    """Get or create the global reranker instance."""
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = Reranker()
    return _reranker_instance
