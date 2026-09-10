# Document Intelligence Agent

A full-stack multimodal RAG system for PDF documents. It parses text **and**
visual layout (tables, charts, diagrams) from PDFs, indexes them for retrieval,
and answers questions using a vision-capable LLM that can look at the actual
page images — not just extracted text. 100% free/local stack: no paid APIs.

## Stack

- **Backend**: Python, FastAPI, PyMuPDF (PDF parsing + page rendering), FAISS
  (local vector store), [Ollama](https://ollama.com) (local embeddings + vision LLM)
- **Frontend**: React, TypeScript, Vite, Tailwind CSS

## How it works

1. **Ingest**: each uploaded PDF is parsed page-by-page with PyMuPDF. Text is
   extracted and chunked; each page is also rendered to a PNG image so visual
   layout (tables, charts, figures) is preserved.
2. **Index**: each text chunk is embedded locally via Ollama
   (`nomic-embed-text`) and stored in a local FAISS index alongside metadata linking it
   back to its source document, page number, and rendered page image.
3. **Query**: a question is embedded and matched against the chunk index. The
   top matching text chunks *and* their corresponding page images are sent
   together to a vision-capable Ollama model (`llava` by default), which can
   read both the text and the visual layout to answer.
4. **Cite**: the response is returned with citations (document, page number,
   thumbnail) so answers are traceable back to the source page.

## Prerequisites

- [Ollama](https://ollama.com) installed and running locally
- Python 3.11+
- Node.js 18+
- (Optional) Docker + Docker Compose

Pull the local models once:

```bash
ollama pull llava
ollama pull nomic-embed-text
```

`llava` (~4.7GB) is the default vision model — a good balance of quality and
resource use on CPU. If you have more RAM/GPU available, swap in a stronger
model such as `llama3.2-vision` or `qwen2-vl` by setting
`OLLAMA_VISION_MODEL` in your `.env`.

## Local development (recommended)

**Backend**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
copy .env.example .env       # Windows; `cp` on macOS/Linux
uvicorn app.main:app --reload --port 8000
```

**Frontend** (in a second terminal)

```bash
cd frontend
npm install
copy .env.example .env       # Windows; `cp` on macOS/Linux
npm run dev
```

Open http://localhost:5173, upload a PDF, wait for it to finish processing,
and start asking questions.

## Docker Compose

Make sure Ollama is running on the host machine (Docker Desktop exposes it via
`host.docker.internal`), then:

```bash
docker compose up --build
```

Backend: http://localhost:8000 · Frontend: http://localhost:5173

On Linux, `host.docker.internal` requires the `extra_hosts` entry already
present in `docker-compose.yml`; if Ollama still isn't reachable, run it with
`OLLAMA_HOST=0.0.0.0` and point `OLLAMA_BASE_URL` at the host's LAN IP instead.

## API overview

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/documents` | Upload a PDF (multipart `file`); processed in the background |
| `GET` | `/api/documents` | List documents and their processing status |
| `DELETE` | `/api/documents/{id}` | Remove a document and its index entries |
| `GET` | `/api/documents/{id}/pages/{n}/image` | Rendered PNG of a given page |
| `POST` | `/api/query` | `{ question, doc_ids?, top_k? }` → answer + citations |
| `POST` | `/api/documents/{id}/highlight` | `{ page_number, text, color? }` → highlight matching text |
| `POST` | `/api/documents/{id}/note` | `{ page_number, x, y, text }` → sticky-note annotation |
| `POST` | `/api/documents/{id}/redact` | `{ text, page_number? }` → permanently black out matching text |
| `DELETE` | `/api/documents/{id}/pages/{n}` | Delete a page |
| `POST` | `/api/documents/{id}/pages/{n}/rotate` | `{ degrees }` → rotate a page (multiple of 90) |
| `POST` | `/api/documents/{id}/pages/reorder` | `{ order: number[] }` → reorder pages |
| `GET` | `/api/documents/{id}/form-fields` | List detected AcroForm fields |
| `POST` | `/api/documents/{id}/form-fields` | `{ values: {name: value} }` → fill form fields |
| `POST` | `/api/documents/{id}/reset` | Discard all edits, revert to the original upload |
| `GET` | `/api/documents/{id}/download` | Download the current (possibly edited) PDF |

### Modifying documents

Click the pencil icon next to a ready document to open the editor: rotate,
reorder, or delete pages; highlight or permanently redact matching text;
drop sticky notes by clicking a page thumbnail; and fill any detected form
fields. Edits are applied to a working copy (`backend/data/storage/{id}/working.pdf`)
— the original upload is never touched, and "Reset to original" discards all
edits. Edits that change extractable text (redact, delete/reorder pages, fill
forms) automatically re-index the document so chat answers and citations stay
in sync; cosmetic edits (highlight, note, rotate) only re-render the affected
page images.

## Configuration

All config is via environment variables (see `.env.example` files):

| Variable | Default | Description |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server address |
| `OLLAMA_VISION_MODEL` | `llava` | Vision-capable chat model used to answer queries |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model used for retrieval |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | CORS origins allowed to call the API |
| `VITE_API_BASE_URL` | `http://localhost:8000` | API base URL the frontend calls |

## Notes

- Document metadata is stored as JSON on disk (`backend/data/storage`); the
  vector index lives in `backend/data/vector_store`. Both are gitignored and
  persist across restarts.
- Everything runs locally — no API keys, no billed services.

## Troubleshooting

**`ollama._types.ResponseError: llama-server process has terminated ... CUDA error`**
(Windows, NVIDIA GPU) — Ollama's GPU backend can crash on some driver/CUDA
combinations. Force CPU-only inference by setting `CUDA_VISIBLE_DEVICES=-1`
as a system/user environment variable, then restart Ollama (quit it from the
tray icon and relaunch). Embeddings still run fine; only the vision model
call is affected.
