# 🔤 Hebrew RAG System – עברית RAG

A complete Retrieval-Augmented Generation (RAG) system for Hebrew EPUB books, featuring:
- 🔍 **Hybrid retrieval**: Semantic (LaBSE) + BM25 lexical search  
- 🎯 **Cross-encoder reranking** for precision  
- 🤖 **Ollama LLM** (qwen2.5:14b-instruct) for Hebrew answer generation  
- 🗂️ **ChromaDB** vector store  
- ✨ **RTL glassmorphism UI** with streaming responses  

---

## Architecture

```
atalefim.epub
    ↓ EPUB Extractor (ebooklib)
    ↓ Hebrew Normalizer (Unicode NFC, nikud removal)
    ↓ Structure-Aware Chunker (~300 tokens, 50 overlap)
    ↓ LaBSE Embeddings (sentence-transformers)
    ↓ ChromaDB Vector Store
    
Query → Hybrid Retrieval (Semantic + BM25 via RRF)
      → Cross-Encoder Reranker
      → Top 5 Chunks
      → Ollama qwen2.5:14b-instruct (Hebrew)
      → Streaming Answer + Sources
```

## Quick Start

### 1. Prerequisites
- Python 3.9+
- [Ollama](https://ollama.ai) with `qwen2.5:14b-instruct` installed

### 2. Start the System
```bat
double-click start.bat
```
Or manually:
```bash
# Create and activate virtualenv
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r backend\requirements.txt

# Start the API server
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Index the Book
- Open http://localhost:8000 in your browser
- Click **"טעינת ספר"** (Load Book) in the top right
- Click **"התחל טעינה"** (Start Ingestion)
- Wait for indexing to complete (~2-5 minutes for LaBSE to embed all chunks)

Or via command line:
```bash
cd backend
python ingest.py
# Force re-index:
python ingest.py --clear
```

### 4. Ask Questions
Type any question in Hebrew in the chat box!

---

## Project Structure

```
Hebrew_RAG/
├── backend/
│   ├── main.py              # FastAPI app (routes, streaming)
│   ├── epub_extractor.py    # EPUB → structured chapters
│   ├── hebrew_normalizer.py # Unicode / RTL / nikud cleanup
│   ├── chunker.py           # ~300-token overlapping chunks
│   ├── embedder.py          # LaBSE sentence-transformers
│   ├── vector_store.py      # ChromaDB operations
│   ├── retriever.py         # Hybrid BM25 + semantic (RRF)
│   ├── reranker.py          # Cross-encoder reranking
│   ├── llm.py               # Ollama streaming integration
│   ├── ingest.py            # Standalone ingestion script
│   └── requirements.txt
├── frontend/
│   ├── index.html           # RTL Hebrew chat UI
│   ├── style.css            # Glassmorphism dark design
│   └── app.js               # Chat + SSE streaming logic
├── data/
│   └── atalefim.epub        # Hebrew EPUB source
├── chroma_db/               # ChromaDB persistent storage
├── .env                     # Configuration
└── start.bat                # One-click startup
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/status` | System status (vector store + Ollama) |
| POST | `/api/ingest` | Trigger EPUB ingestion |
| GET | `/api/ingestion-status` | Poll ingestion progress |
| POST | `/api/query` | Query (returns JSON) |
| POST | `/api/query/stream` | Query with SSE streaming |
| GET | `/api/sources` | List indexed chapters |
| GET | `/docs` | Interactive Swagger UI |

### Example Query

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "מי הדמויות הראשיות בסיפור?",
    "top_k": 5,
    "use_hybrid": true,
    "use_reranker": true
  }'
```

---

## Configuration (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `qwen2.5:14b-instruct` | Ollama model |
| `EMBEDDING_MODEL` | `sentence-transformers/LaBSE` | Embedding model |
| `RERANKER_MODEL` | `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` | Reranker |
| `CHROMA_DB_PATH` | `../chroma_db` | ChromaDB storage path |
| `EPUB_PATH` | `../data/atalefim.epub` | EPUB source path |

---

## Adding More Books

1. Copy your EPUB file to `data/`
2. POST to `/api/ingest` with `epub_path` pointing to the new file
3. Or update `EPUB_PATH` in `.env` and re-run ingestion

---

## Technology Stack

| Component | Library |
|-----------|---------|
| Backend | FastAPI + Uvicorn |
| EPUB Parsing | ebooklib + BeautifulSoup4 |
| Embeddings | sentence-transformers (LaBSE) |
| Vector Store | ChromaDB |
| Lexical Search | rank-bm25 |
| Reranking | cross-encoder/mmarco-mMiniLMv2 |
| LLM | Ollama (qwen2.5:14b-instruct) |
| Frontend | Vanilla HTML/CSS/JS (RTL glassmorphism) |
