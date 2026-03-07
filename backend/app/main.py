from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import FRONTEND_URL
from app.api import auth, patients, people, events, items, reminders, notes, query, websocket

app = FastAPI(title="MemoLens API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
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


@app.get("/health")
async def health():
    return {"status": "ok"}
