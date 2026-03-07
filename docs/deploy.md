# Deploy Guide

## Option A: Local full stack (Docker Compose)

```bash
docker compose up --build
```

Services:
- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Postgres: `localhost:5432`
- Redis: `localhost:6379`

## Option B: Hosted demo (recommended)

### Backend (Render/Railway)
1. Deploy `backend/` as a Docker service.
2. Set env vars:
   - `DATABASE_URL`
   - `REDIS_URL`
   - `JWT_SECRET`
   - `FRONTEND_URL`
   - `FRONTEND_URLS`
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
   - `SUPABASE_STORAGE_BUCKET`
3. Ensure startup command runs migrations (included in Dockerfile).
4. Verify `GET /health` is healthy.

### Frontend (Vercel or similar)
1. Deploy `frontend/`.
2. Set env var:
   - `NEXT_PUBLIC_API_URL=https://<your-backend-domain>/api/v1`
3. Redeploy.

### Post-deploy smoke test
1. Register caregiver in frontend.
2. Create patient and copy patient ID.
3. Open dashboard with patient ID and verify event timeline loads.
4. Run Pi stream script against deployed backend:
   - `python pi/stream.py --backend-ws wss://<backend>/ws/stream/<patient_id>`
5. Confirm live events appear in dashboard/timeline.

## Required runtime notes
- WebSocket event feed endpoint: `/ws/events/{patient_id}?token=<jwt>`
- Pi stream endpoint: `/ws/stream/{patient_id}`
- Seed demo data:
  ```bash
  cd backend
  python -m scripts.seed_demo
  ```
