from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import documents, edit, query

app = FastAPI(title="Document Intelligence Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(edit.router)
app.include_router(query.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
