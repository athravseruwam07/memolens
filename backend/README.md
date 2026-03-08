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

### 3.1 (Optional) Install native CV extras
Only needed if you want local `face_recognition`/`dlib` on backend machine:
```bash
pip install -r requirements-cv.txt
```

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env with your Supabase credentials and secrets
# Set FRONTEND_URL / FRONTEND_URLS to your deployed frontend domain(s)
```

### 5. Run database migrations
```bash
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

### 8. Seed demo data
```bash
python -m scripts.seed_demo
```
This creates demo caregiver accounts, one patient, linked caregivers, people, reminders, notes, item states, and events.

### 9. Rehearse the 3-minute demo flow (Step 17)
Use the patient ID printed by the seed script:
```bash
python -m scripts.rehearse_demo --base-url http://localhost:8000 --patient-id <PATIENT_ID>
```
Detailed speaking flow and fallback path:
- `../docs/demo_rehearsal.md`

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health
- Contract doc: `../docs/api.md`

## Deployment

For full deployment instructions (Docker Compose + hosted setup), see:
- `../docs/deploy.md`

## Tech Stack

- **FastAPI** — async web framework
- **SQLAlchemy** (async) — ORM / database access
- **Supabase** (PostgreSQL) — hosted database
- **Celery + Redis** — background job scheduling
- **WebSockets** — real-time Pi frame streaming
- **python-jose** — JWT authentication
- **passlib** — password hashing (bcrypt)
