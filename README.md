# MemoLens

Memory is personal. Losing pieces of it is terrifying.

**MemoLens** is a real-time assistive system for dementia care that helps patients stay oriented and helps caregivers stay informed.  
It combines live camera context, reminder logic, item tracking, and a caregiver live feed into one practical workflow.

Instead of one more static app, MemoLens is designed to answer real moments:
- "Who is this?"
- "Where are my keys?"
- "Did I take my medication?"
- "What do I need to remember today?"

## Why this project exists

Dementia support often breaks down in the small moments: forgotten faces, misplaced essentials, missed reminders, rising caregiver anxiety.

MemoLens focuses on those moments with:
- low-friction patient prompts
- real-time caregiver visibility
- clear event history and item states
- deployable full-stack architecture

## What MemoLens does today

### Core patient support
- Recognizes familiar people from known profiles
- Tracks key daily items and last-seen context
- Triggers contextual reminders (time, person, location, object)
- Answers memory-style queries through a simple query endpoint

### Caregiver support
- Live event feed over WebSocket
- Timeline without manual refresh
- Current item states (room, timestamp, confidence)
- Daily notes and reminder management

### System reliability
- Seed script for realistic demo data
- Deployment validation script (env + migration + health checks)
- End-to-end smoke test (register/login -> patient -> stream -> live events -> query)
- Rehearsal script for a repeatable 3-minute demo flow

## Architecture at a glance

`Pi/Webcam Stream -> FastAPI Backend -> CV + Reminder Logic -> Postgres Event/State Store -> Live WebSocket Updates -> Caregiver/Patient UI`

### Main components
- `backend/` FastAPI APIs, DB models, auth, event processing, scripts
- `frontend/` Next.js caregiver + patient experiences
- `pi/` WebSocket frame streaming client
- `docs/` API contract, deploy guide, demo rehearsal guide

## Repo structure

```text
memolens/
  backend/
  frontend/
  pi/
  cv/
  docs/
  docker-compose.yml
  render.yaml
```

## Quickstart (local)

### 1) Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend URLs:
- Health: `http://localhost:8000/health`
- Swagger: `http://localhost:8000/docs`

### 2) Frontend
```bash
cd frontend
npm install
npm run dev
```

Frontend URL:
- App: `http://localhost:3000`

### 3) Optional Pi stream test
```bash
cd pi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python stream.py --backend-ws ws://localhost:8000/ws/stream/<PATIENT_ID> --room kitchen
```

## Demo tooling (recommended)

### Seed realistic demo state
```bash
cd backend
source venv/bin/activate
python -m scripts.seed_demo
```

### Validate deployment readiness
```bash
python -m scripts.deploy_check --backend-url https://YOUR_BACKEND_DOMAIN
```

### Run full smoke test
```bash
python -m scripts.smoke_e2e --base-url https://YOUR_BACKEND_DOMAIN
```

### Rehearse demo flow
```bash
python -m scripts.rehearse_demo --base-url https://YOUR_BACKEND_DOMAIN --patient-id YOUR_PATIENT_ID
```

## Deployment

Use the full instructions in:
- `docs/deploy.md`

Typical production setup:
- Backend: Render/Railway (Docker service from `backend/`)
- Frontend: Vercel (`frontend/`)
- Postgres: hosted managed instance
- Redis: hosted managed instance

After deploy:
1. Verify `GET /health`
2. Run `deploy_check`
3. Run `smoke_e2e`
4. Seed demo data if needed
5. Rehearse the demo with `rehearse_demo`

## API and Realtime

See:
- `docs/api.md`

Key endpoints:
- REST: `/api/v1/...`
- Stream WS: `/ws/stream/{patient_id}`
- Caregiver events WS: `/ws/events/{patient_id}?token=<jwt>`

## Current status

- Core MVP pipeline implemented
- Real-time caregiver feed implemented
- Reminder and memory query flow implemented
- End-to-end smoke and deployment checks implemented
- Demo rehearsal flow implemented

## Vision

MemoLens is built around one principle:

**Reduce confusion for patients and reduce uncertainty for caregivers, in real time.**

