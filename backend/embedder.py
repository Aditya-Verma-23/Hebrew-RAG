"""
embedder.py
-----------
Wrapper around sentence-transformers for Hebrew/multilingual embeddings.
Uses LaBSE model which has excellent Hebrew support.
"""

import os
from typing import List, Optional
from functools import lru_cache

from sentence_transformers import SentenceTransformer


# Model options:
# - "sentence-transformers/LaBSE" – excellent Hebrew, ~470MB
# - "intfloat/multilingual-e5-large" – best quality, ~1.2GB
# - "paraphrase-multilingual-mpnet-base-v2" – good, ~280MB
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/LaBSE")
EMBEDDING_DIM = 768  # LaBSE dimension

# Instruction prefix for E5 models (not needed for LaBSE)
E5_QUERY_PREFIX = "query: "
E5_DOC_PREFIX = "passage: "


class Embedder:
    """Singleton-style embedder for multilingual text."""
    
    def __init__(self, model_name: str = EMBEDDING_MODEL):
        print(f"[Embedder] Loading model: {model_name}")
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.is_e5 = "e5" in model_name.lower()
        dim = self.model.get_embedding_dimension() if hasattr(self.model, 'get_embedding_dimension') else self.model.get_sentence_embedding_dimension()
        print(f"[Embedder] Model loaded. Embedding dim: {dim}")
    
    def embed_documents(self, texts: List[str], batch_size: int = 32, show_progress: bool = True) -> List[List[float]]:
        """Embed a list of documents (passages)."""
        if self.is_e5:
            texts = [E5_DOC_PREFIX + t for t in texts]
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return embeddings.tolist()
    
    def embed_query(self, query: str) -> List[float]:
        """Embed a single query."""
        if self.is_e5:
            query = E5_QUERY_PREFIX + query
        
        embedding = self.model.encode(
            query,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return embedding.tolist()
    
    def get_dimension(self) -> int:
        """Return embedding dimension."""
        if hasattr(self.model, 'get_embedding_dimension'):
            return self.model.get_embedding_dimension()
        return self.model.get_sentence_embedding_dimension()


# Module-level singleton
_embedder_instance: Optional[Embedder] = None


def get_embedder() -> Embedder:
    """Get or create the global embedder instance."""
    global _embedder_instance
    if _embedder_instance is None:
        _embedder_instance = Embedder()
    return _embedder_instance


if __name__ == "__main__":
    embedder = get_embedder()
    texts = ["שלום עולם", "Hello World", "מה שלומך?"]
    embeddings = embedder.embed_documents(texts)
    print(f"Embedded {len(embeddings)} texts, dim={len(embeddings[0])}")
    
    query_emb = embedder.embed_query("שלום")
    print(f"Query embedding dim: {len(query_emb)}")
