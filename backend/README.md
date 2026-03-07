# MemoLens Backend

AI-powered cognitive support system for dementia patients.

## Setup

### 1. Clone and navigate
```bash
cd backend
```

### 2. Create virtual environment
```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env with your Supabase credentials and secrets
```

### 5. Run database migrations
```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### 6. Start the server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. (Optional) Start Celery worker + beat
```bash
celery -A app.workers.celery_app worker --loglevel=info
celery -A app.workers.celery_app beat --loglevel=info
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

## Tech Stack

- **FastAPI** — async web framework
- **SQLAlchemy** (async) — ORM / database access
- **Supabase** (PostgreSQL) — hosted database
- **Celery + Redis** — background job scheduling
- **WebSockets** — real-time Pi frame streaming
- **python-jose** — JWT authentication
- **passlib** — password hashing (bcrypt)
