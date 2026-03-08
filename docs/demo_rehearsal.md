# Demo Rehearsal (Step 17)

This is the fixed 3-minute demo flow and rehearsal checklist.

## Goal
- Rehearse the exact sequence:
  - intro problem
  - face/object intelligence in context
  - "Where are my keys?" query
  - caregiver live dashboard/timeline updates
  - impact close

## Preflight (2 minutes)
1. Start backend on `http://localhost:8000` (or deployed URL).
2. Seed demo data:
   ```bash
   cd backend
   python -m scripts.seed_demo
   ```
3. Save the printed `Patient ID`.
4. Keep caregiver dashboard and timeline open for that patient.

## Automated rehearsal check
Run this before presenting:

```bash
cd backend
python -m scripts.rehearse_demo \
  --base-url http://localhost:8000 \
  --patient-id <PATIENT_ID>
```

What it validates:
- caregiver auth and patient access
- query path (`Where are my keys?`, `Did I take my medication?`)
- stream ingestion (`/ws/stream/{patient_id}`)
- live feed path (`/ws/events/{patient_id}`)
- fallback proof via REST events (`/patients/{patient_id}/events`)
- item state update confirmation

## 3-minute speaking track
- `0:00-0:30` Problem:
  - "Dementia patients forget people, items, and tasks; caregivers need live visibility."
- `0:30-1:20` Live context:
  - Send stream frames.
  - Show object/person detection messages and reminder prompts.
- `1:20-2:00` Memory query:
  - Ask: "Where are my keys?"
  - Ask: "Did I take my medication?"
- `2:00-2:40` Caregiver visibility:
  - Show timeline/dashboard updating without manual refresh.
- `2:40-3:00` Impact close:
  - "MemoLens gives immediate memory support for patients and confidence for caregivers."

## Backup path (if WebSocket live feed fails)
Use REST endpoints as proof of the same pipeline:
1. Item evidence:
   - `GET /api/v1/patients/{patient_id}/events?type=item_seen&limit=10`
2. Reminder evidence:
   - `GET /api/v1/patients/{patient_id}/events?type=reminder_triggered&limit=10`
3. State evidence:
   - `GET /api/v1/patients/{patient_id}/item-states/`

The audience still sees the full chain: stream -> DB/event log -> retrievable memory state.
