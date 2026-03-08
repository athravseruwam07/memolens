from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import FRONTEND_URL, FRONTEND_URLS, LOCAL_UPLOAD_DIR, SUPABASE_STORAGE_REQUIRED
from app.api import auth, patients, people, events, items, reminders, notes, query, websocket

app = FastAPI(title="MemoLens API", version="1.0.0")

allowed_origins = [FRONTEND_URL, "http://localhost:3000", *FRONTEND_URLS]
allowed_origins = list(dict.fromkeys([u for u in allowed_origins if u]))

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
prefix = "/api/v1"
app.include_router(auth.router, prefix=prefix)
app.include_router(patients.router, prefix=prefix)
app.include_router(people.router, prefix=prefix)
app.include_router(events.router, prefix=prefix)
app.include_router(items.router, prefix=prefix)
app.include_router(reminders.router, prefix=prefix)
app.include_router(notes.router, prefix=prefix)
app.include_router(query.router, prefix=prefix)

# WebSocket (no prefix — mounted at root)
app.include_router(websocket.router)

# Local upload fallback serving (/uploads/*) when explicitly enabled.
if not SUPABASE_STORAGE_REQUIRED:
    Path(LOCAL_UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=LOCAL_UPLOAD_DIR), name="uploads")


@app.get("/health")
async def health():
    return {"status": "ok"}
