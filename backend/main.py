"""
main.py
-------
FastAPI backend for Hebrew RAG system.
Endpoints:
  POST /api/ingest        - Trigger EPUB ingestion
  POST /api/query         - Query the RAG system
  GET  /api/status        - System status
  GET  /api/sources       - List indexed chapters
  GET  /api/health        - Health check
  WS   /ws/chat           - WebSocket two-way real-time chat
"""

import os
import sys
import asyncio
import threading
from pathlib import Path
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
import json

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from llm import generate_answer, generate_answer_streaming, check_ollama_status
from retriever import get_retriever
from reranker import get_reranker
from vector_store import get_vector_store
from hebrew_normalizer import normalize_hebrew


# ─── Pydantic Models ────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="Hebrew query string")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")
    use_hybrid: bool = Field(default=True, description="Use hybrid retrieval (semantic + BM25)")
    use_reranker: bool = Field(default=True, description="Use cross-encoder reranker")
    stream: bool = Field(default=False, description="Stream the response")
    temperature: float = Field(default=0.1, ge=0, le=1, description="LLM temperature")
    n_candidates: int = Field(default=20, ge=5, le=50, description="Retrieval candidates before reranking")
    book_filename: Optional[str] = Field(default=None, description="Filter search to specific book")

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Query cannot be empty or whitespace")
        return stripped

    @field_validator("top_k")
    @classmethod
    def top_k_le_candidates(cls, v: int, info) -> int:
        return v


class IngestRequest(BaseModel):
    epub_path: Optional[str] = Field(default=None, description="Path to EPUB file")
    clear_existing: bool = Field(default=False, description="Clear existing collection")
    chunk_size: int = Field(default=300, ge=100, le=1000)
    overlap: int = Field(default=50, ge=0, le=200)
    remove_nikud: bool = Field(default=True, description="Strip Hebrew diacritical marks")


class SourceChunk(BaseModel):
    id: str
    text: str
    chapter_title: str
    chapter_index: int
    book_title: str
    chunk_index: int
    rerank_score: Optional[float] = None
    search_type: str = "hybrid"


class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[SourceChunk]
    model: str
    n_chunks_retrieved: int


# ─── Ingestion State ─────────────────────────────────────────────────────────

ingestion_state = {
    "status": "idle",  # idle | running | done | error
    "message": "",
    "progress": {},
}


def _run_ingestion_background(epub_path: str, clear: bool, chunk_size: int, overlap: int, remove_nikud: bool):
    """Run ingestion in background thread."""
    global ingestion_state
    try:
        ingestion_state["status"] = "running"
        ingestion_state["message"] = "Running ingestion..."
        
        from ingest import run_ingestion
        result = run_ingestion(
            epub_path=epub_path,
            chunk_size=chunk_size,
            overlap=overlap,
            clear_existing=clear,
            remove_nikud=remove_nikud,
        )
        
        # Invalidate BM25 index after ingestion
        retriever = get_retriever()
        retriever.invalidate_bm25()
        
        ingestion_state["status"] = "done"
        ingestion_state["message"] = "Ingestion completed successfully."
        ingestion_state["progress"] = result
    
    except Exception as e:
        ingestion_state["status"] = "error"
        ingestion_state["message"] = str(e)


# ─── FastAPI App ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize components on startup."""
    print("[API] Starting Hebrew RAG API...")
    # Pre-initialize components
    try:
        store = get_vector_store()
        print(f"[API] Vector store ready. Documents: {store.count()}")
    except Exception as e:
        print(f"[API] Warning: Vector store init error: {e}")
    yield
    print("[API] Shutting down...")


app = FastAPI(
    title="Hebrew RAG API",
    description="Hebrew Retrieval-Augmented Generation API powered by LaBSE + ChromaDB + Ollama",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """Basic health check."""
    return {"status": "ok", "message": "Hebrew RAG API is running"}


@app.get("/api/status")
async def get_status():
    """Get system status including vector store, Ollama, and ingestion state."""
    store = get_vector_store()
    ollama_status = check_ollama_status()
    
    return {
        "vector_store": {
            "documents": store.count(),
            "collection": store.collection_name,
        },
        "ollama": ollama_status,
        "ingestion": ingestion_state,
    }


@app.post("/api/ingest")
async def ingest(request: IngestRequest, background_tasks: BackgroundTasks):
    """Trigger EPUB ingestion in background."""
    global ingestion_state
    
    if ingestion_state["status"] == "running":
        raise HTTPException(status_code=409, detail="Ingestion already running")
    
    # Resolve EPUB path
    data_dir = Path(__file__).parent.parent / "data"
    if not request.epub_path:
        # Default path relative to backend
        epub_path = str(data_dir / "atalefim.epub")
    else:
        # Check if they provided an absolute path or just a filename
        req_path = Path(request.epub_path)
        if not req_path.is_absolute():
            epub_path = str(data_dir / request.epub_path)
        else:
            epub_path = str(req_path)
    
    epub_path = str(Path(epub_path).resolve())
    if not os.path.exists(epub_path):
        raise HTTPException(status_code=404, detail=f"EPUB file not found: {epub_path}")
    
    # Reset state
    ingestion_state["status"] = "running"
    ingestion_state["message"] = "Starting ingestion..."
    ingestion_state["progress"] = {}
    
    # Run in background thread (not async, since sentence-transformers is sync)
    thread = threading.Thread(
        target=_run_ingestion_background,
        args=(epub_path, request.clear_existing, request.chunk_size, request.overlap, request.remove_nikud),
        daemon=True,
    )
    thread.start()
    
    return {"status": "started", "message": "Ingestion started in background"}


@app.get("/api/ingestion-status")
async def get_ingestion_status():
    """Get current ingestion status."""
    return ingestion_state


@app.post("/api/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Query the Hebrew RAG system.
    Returns answer + source chunks.
    """
    store = get_vector_store()
    
    if store.count() == 0:
        raise HTTPException(
            status_code=503,
            detail="No documents indexed. Please run ingestion first via POST /api/ingest"
        )
    
    # Normalize query
    query_normalized = normalize_hebrew(request.query, remove_nikud=False)
    
    where = None
    if request.book_filename:
        where = {"book_title": request.book_filename}

    # Retrieve candidates
    retriever = get_retriever()
    candidates = retriever.retrieve(
        query=query_normalized,
        n_results=request.n_candidates,
        use_hybrid=request.use_hybrid,
        where=where,
    )
    
    if not candidates:
        raise HTTPException(status_code=404, detail="No relevant documents found")
    
    # Rerank
    if request.use_reranker:
        reranker = get_reranker()
        top_chunks = reranker.rerank(
            query=query_normalized,
            candidates=candidates,
            top_k=request.top_k,
        )
    else:
        top_chunks = candidates[:request.top_k]
    
    # Generate answer
    answer = generate_answer(
        query=request.query,
        chunks=top_chunks,
        temperature=request.temperature,
    )
    
    # Format sources
    sources = []
    for chunk in top_chunks:
        meta = chunk.get("metadata", {})
        sources.append(SourceChunk(
            id=chunk["id"],
            text=chunk["text"],
            chapter_title=meta.get("chapter_title", ""),
            chapter_index=meta.get("chapter_index", 0),
            book_title=meta.get("book_title", ""),
            chunk_index=meta.get("chunk_index", 0),
            rerank_score=chunk.get("rerank_score"),
            search_type=chunk.get("search_type", "hybrid"),
        ))
    
    from llm import LLM_MODEL
    return QueryResponse(
        query=request.query,
        answer=answer,
        sources=sources,
        model=LLM_MODEL,
        n_chunks_retrieved=len(candidates),
    )


@app.post("/api/query/stream")
async def query_stream(request: QueryRequest):
    """
    Stream Hebrew RAG response as Server-Sent Events.
    """
    store = get_vector_store()
    
    if store.count() == 0:
        raise HTTPException(
            status_code=503,
            detail="No documents indexed. Please run ingestion first."
        )
    
    # Normalize query
    query_normalized = normalize_hebrew(request.query, remove_nikud=False)
    
    # Retrieve and rerank synchronously first
    retriever = get_retriever()
    candidates = retriever.retrieve(
        query=query_normalized,
        n_results=request.n_candidates,
        use_hybrid=request.use_hybrid,
    )
    
    if not candidates:
        raise HTTPException(status_code=404, detail="No relevant documents found")
    
    if request.use_reranker:
        reranker = get_reranker()
        top_chunks = reranker.rerank(
            query=query_normalized,
            candidates=candidates,
            top_k=request.top_k,
        )
    else:
        top_chunks = candidates[:request.top_k]
    
    # Build sources metadata to send first
    sources = []
    for chunk in top_chunks:
        meta = chunk.get("metadata", {})
        sources.append({
            "id": chunk["id"],
            "chapter_title": meta.get("chapter_title", ""),
            "chapter_index": meta.get("chapter_index", 0),
            "book_title": meta.get("book_title", ""),
            "chunk_index": meta.get("chunk_index", 0),
            "text_preview": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
            "rerank_score": chunk.get("rerank_score"),
        })
    
    import json
    
    async def event_generator():
        # First send sources as a special event
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
        
        # Then stream the answer
        loop = asyncio.get_event_loop()
        
        def blocking_stream():
            return list(generate_answer_streaming(
                query=request.query,
                chunks=top_chunks,
                temperature=request.temperature,
            ))
        
        tokens = await loop.run_in_executor(None, blocking_stream)
        
        for token in tokens:
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/sources")
async def get_sources():
    """List all indexed chapters."""
    store = get_vector_store()
    chapters = store.get_chapters()
    return {
        "total_documents": store.count(),
        "chapters": chapters,
    }


@app.get("/api/books")
async def get_books():
    """List all EPUB files in the data directory and their index status."""
    data_dir = Path(__file__).parent.parent / "data"
    store = get_vector_store()
    is_indexed = store.count() > 0
    
    books = []
    if data_dir.exists():
        for file in data_dir.glob("*.epub"):
            books.append({
                "filename": file.name,
                "status": "Ready" if is_indexed else "Not indexed"
            })
            
    return {"books": books}

# ─── WebSocket – Two-Way Real-Time Chat ─────────────────────────────────────

# WebSocket message protocol (client → server):
#   { "type": "ping" }
#   { "type": "query", "query": "...", "settings": { top_k, temperature, ... } }
#   { "type": "cancel" }
#
# WebSocket message protocol (server → client):
#   { "type": "pong", "docs_count": N, "model": "..." }
#   { "type": "validation_error", "message": "..." }
#   { "type": "sources", "sources": [...] }
#   { "type": "token", "content": "..." }
#   { "type": "done", "total_tokens": N }
#   { "type": "error", "message": "..." }

active_ws_sessions: set = set()


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """Two-way WebSocket endpoint for real-time Hebrew RAG queries."""
    await websocket.accept()
    active_ws_sessions.add(id(websocket))
    cancelled = False
    print(f"[WS] Client connected. Active sessions: {len(active_ws_sessions)}")

    async def send(payload: dict):
        try:
            await websocket.send_text(json.dumps(payload, ensure_ascii=False))
        except Exception:
            pass

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await send({"type": "error", "message": "Invalid JSON message"})
                continue

            msg_type = msg.get("type", "")

            # ── Ping / health check ──────────────────────────────────────────
            if msg_type == "ping":
                store = get_vector_store()
                ollama = check_ollama_status()
                await send({
                    "type": "pong",
                    "docs_count": store.count(),
                    "model": ollama.get("model", ""),
                    "ollama_running": ollama.get("running", False),
                    "model_available": ollama.get("model_available", False),
                })
                continue

            # ── Cancel ──────────────────────────────────────────────────────
            if msg_type == "cancel":
                cancelled = True
                await send({"type": "cancelled", "message": "Query cancelled"})
                continue

            # ── Query ────────────────────────────────────────────────────────
            if msg_type == "query":
                cancelled = False
                raw_query = msg.get("query", "").strip()
                settings = msg.get("settings", {})

                # ── Server-side validation ───────────────────────────────────
                errors = []
                if not raw_query:
                    errors.append("Query cannot be empty")
                elif len(raw_query) > 2000:
                    errors.append("Query too long (max 2000 characters)")
                elif len(raw_query) < 2:
                    errors.append("Query too short (min 2 characters)")

                top_k = int(settings.get("top_k", 5))
                temperature = float(settings.get("temperature", 0.1))
                use_hybrid = bool(settings.get("use_hybrid", True))
                use_reranker = bool(settings.get("use_reranker", True))
                n_candidates = int(settings.get("n_candidates", 20))

                if not (1 <= top_k <= 20):
                    errors.append("top_k must be between 1 and 20")
                if not (0.0 <= temperature <= 1.0):
                    errors.append("temperature must be between 0.0 and 1.0")
                if not (5 <= n_candidates <= 50):
                    errors.append("n_candidates must be between 5 and 50")

                if errors:
                    await send({"type": "validation_error", "errors": errors})
                    continue

                # ── Check index ──────────────────────────────────────────────
                store = get_vector_store()
                if store.count() == 0:
                    await send({
                        "type": "error",
                        "message": "No documents indexed. Please run ingestion first."
                    })
                    continue

                # ── Normalize query ──────────────────────────────────────────
                query_norm = normalize_hebrew(raw_query, remove_nikud=False)

                # ── Retrieve ─────────────────────────────────────────────────
                await send({"type": "status", "message": "מאחזר קטעים רלוונטיים..."})
                retriever = get_retriever()

                loop = asyncio.get_event_loop()
                candidates = await loop.run_in_executor(
                    None, lambda: retriever.retrieve(
                        query=query_norm,
                        n_results=n_candidates,
                        use_hybrid=use_hybrid,
                    )
                )

                if not candidates:
                    await send({"type": "error", "message": "לא נמצאו קטעים רלוונטיים"})
                    continue

                # ── Rerank ───────────────────────────────────────────────────
                if use_reranker:
                    await send({"type": "status", "message": "מדרג תוצאות..."})
                    reranker = get_reranker()
                    top_chunks = await loop.run_in_executor(
                        None, lambda: reranker.rerank(
                            query=query_norm,
                            candidates=candidates,
                            top_k=top_k,
                        )
                    )
                else:
                    top_chunks = candidates[:top_k]

                # ── Send sources ─────────────────────────────────────────────
                sources_payload = []
                for chunk in top_chunks:
                    meta = chunk.get("metadata", {})
                    sources_payload.append({
                        "id": chunk["id"],
                        "text": chunk["text"],
                        "text_preview": chunk["text"][:250] + "…" if len(chunk["text"]) > 250 else chunk["text"],
                        "chapter_title": meta.get("chapter_title", ""),
                        "chapter_index": meta.get("chapter_index", 0),
                        "book_title": meta.get("book_title", ""),
                        "chunk_index": meta.get("chunk_index", 0),
                        "rerank_score": chunk.get("rerank_score"),
                        "search_type": chunk.get("search_type", "hybrid"),
                    })

                await send({"type": "sources", "sources": sources_payload, "total_candidates": len(candidates)})

                # ── Stream answer ────────────────────────────────────────────
                await send({"type": "status", "message": "מייצר תשובה..."})

                token_count = 0

                def stream_tokens():
                    return list(generate_answer_streaming(
                        query=raw_query,
                        chunks=top_chunks,
                        temperature=temperature,
                    ))

                tokens = await loop.run_in_executor(None, stream_tokens)

                for token in tokens:
                    if cancelled:
                        await send({"type": "cancelled", "message": "Query was cancelled"})
                        break
                    if token:
                        await send({"type": "token", "content": token})
                        token_count += 1
                else:
                    await send({"type": "done", "total_tokens": token_count})

                continue

            # ── Unknown message type ─────────────────────────────────────────
            await send({"type": "error", "message": f"Unknown message type: {msg_type}"})

    except WebSocketDisconnect:
        print(f"[WS] Client disconnected.")
    except Exception as e:
        print(f"[WS] Error: {e}")
        try:
            await send({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        active_ws_sessions.discard(id(websocket))
        print(f"[WS] Cleaned up. Active sessions: {len(active_ws_sessions)}")


@app.get("/api/ws-sessions")
async def get_ws_sessions():
    return {"active_sessions": len(active_ws_sessions)}


# ─── Serve Frontend ──────────────────────────────────────────────────────────

frontend_path = Path(__file__).parent.parent / "frontend-react" / "dist"
if not frontend_path.exists():
    # Fall back to old vanilla frontend
    frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(Path(__file__).parent)],
    )
