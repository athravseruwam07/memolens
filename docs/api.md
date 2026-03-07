# MemoLens API Contract

Base URL: `/api/v1`

All endpoints return:

```json
{ "data": {}, "error": null }
```

If an operation fails, `error` is set and `data` may be `null`.

## Auth

### POST `/auth/register`
Request:
```json
{
  "email": "caregiver@example.com",
  "password": "secret",
  "name": "Caregiver Name",
  "role": "caregiver"
}
```
Response `data`:
```json
{
  "user": { "id": "uuid", "email": "...", "name": "...", "role": "caregiver", "created_at": "iso" },
  "token": "jwt"
}
```

### POST `/auth/login`
Request:
```json
{ "email": "caregiver@example.com", "password": "secret" }
```
Response `data`: same shape as register.

### POST `/auth/invite-caregiver` (primary caregiver only)
Auth: Bearer token
Request:
```json
{ "patient_id": "uuid", "email": "newcaregiver@example.com" }
```
Response `data`:
```json
{
  "message": "Caregiver invite created",
  "invite_token": "opaque-token",
  "expires_at": "iso"
}
```

### POST `/auth/accept-invite`
Request:
```json
{
  "token": "opaque-token",
  "name": "New Caregiver",
  "password": "secret123"
}
```
`name` and `password` are required only when invitee account does not exist.

Response `data`:
```json
{
  "message": "Invite accepted",
  "patient_id": "uuid",
  "user": { "id": "uuid", "email": "...", "name": "...", "role": "caregiver", "created_at": "iso" },
  "token": "jwt"
}
```

## Patients

### POST `/patients/`
Auth: caregiver
Request:
```json
{
  "name": "John",
  "age": 78,
  "emergency_contact": { "name": "Sarah", "phone": "+1-555-0100" },
  "tracked_items": ["keys", "phone", "wallet"],
  "common_issues": "Sometimes forgets medication"
}
```

### GET `/patients/{patient_id}`
### PATCH `/patients/{patient_id}`
### GET `/patients/{patient_id}/caregivers`
### DELETE `/patients/{patient_id}/caregivers/{uid}` (primary only)

## Familiar People

### GET `/patients/{patient_id}/people/`
### POST `/patients/{patient_id}/people/`
Multipart form fields:
- `name` (required)
- `relationship`
- `notes`
- `conversation_prompt`
- `importance_level`
- `photos` (0..N image files)

### PATCH `/patients/{patient_id}/people/{pid}`
### DELETE `/patients/{patient_id}/people/{pid}`
### POST `/patients/{patient_id}/people/{pid}/photos`
Multipart field: `photos` (1..N image files)

## Item States

### GET `/patients/{patient_id}/item-states/`
Returns latest known location/state per item.

## Reminders

### GET `/patients/{patient_id}/reminders/`
### POST `/patients/{patient_id}/reminders/`
Request:
```json
{
  "type": "time",
  "trigger_meta": { "time": "09:00", "cooldown_seconds": 60 },
  "message": "Take your medication",
  "active": true
}
```

Reminder `type` values supported by trigger engine:
- `time`
- `person`
- `location`
- `object`

`trigger_meta` examples:
- time: `{ "time": "09:00" }`
- person: `{ "person_id": "uuid-or-external-id" }`
- location: `{ "room": "kitchen" }` or `{ "rooms": ["kitchen", "hall"] }`
- object: `{ "item": "keys" }` or `{ "items": ["keys", "wallet"], "mode": "missing_before_exit" }`

### PATCH `/patients/{patient_id}/reminders/{rid}`
### DELETE `/patients/{patient_id}/reminders/{rid}`

## Daily Notes

### GET `/patients/{patient_id}/daily-notes?date=YYYY-MM-DD`
### POST `/patients/{patient_id}/daily-notes`
Request:
```json
{ "content": "Sarah is visiting for lunch." }
```

## Events

### POST `/events`
Auth required and must have access to `patient_id` in body.

Request:
```json
{ "patient_id": "uuid", "type": "item_seen", "payload": { "item_name": "keys" } }
```

### GET `/patients/{patient_id}/events?type=item_seen&limit=50&offset=0`

## Query

### POST `/query`
Request:
```json
{ "patient_id": "uuid", "question": "Where are my keys?" }
```
Response `data`:
```json
{
  "question": "Where are my keys?",
  "answer_type": "item_location",
  "results": []
}
```

## WebSocket Stream

### `ws://<host>/ws/stream/{patient_id}`

Client -> Server payloads:
1. Legacy format: raw base64 JPEG string
2. JSON envelope:
```json
{
  "frame_b64": "<base64-jpeg>",
  "room": "kitchen",
  "near_exit": false,
  "detections": [
    { "item": "keys", "room": "kitchen", "confidence": 0.91 }
  ]
}
```

Server -> Client message types:
- person match:
```json
{ "type": "person", "name": "Sarah", "relationship": "daughter", "notes": "...", "conversation_prompt": "..." }
```
- item detection:
```json
{ "type": "item", "item_name": "keys", "room": "kitchen", "confidence": 0.91 }
```
- reminder:
```json
{ "type": "reminder", "message": "Take your medication" }
```
- no event:
```json
{ "type": "no_match" }
```

## Caregiver Live Event WebSocket

### `ws://<host>/ws/events/{patient_id}?token=<jwt>`

- Requires valid caregiver JWT token in query string.
- User must be linked to the patient.
- Emits one message per event:

```json
{
  "type": "event",
  "event": {
    "id": "uuid",
    "patient_id": "uuid",
    "type": "item_seen",
    "payload": {},
    "occurred_at": "iso"
  }
}
```
