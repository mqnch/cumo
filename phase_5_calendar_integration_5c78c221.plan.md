---
name: Phase 5 Calendar Integration
overview: Implement Google Calendar OAuth and a Huey-backed background task to push parsed events to a user-selected Google Calendar, wired to a new /schedule endpoint called by the UI on Enter.
todos:
  - id: auth-module
    content: Create backend/auth.py to run InstalledAppFlow loopback OAuth and persist backend/token.json, exposing get_calendar_service().
    status: pending
  - id: calendar-picker
    content: Add backend endpoints to list calendars (GET /calendars) and store a selectedCalendarId (GET/POST /settings or POST /settings/calendar).
    status: pending
    dependencies:
      - auth-module
  - id: push-task
    content: Add Huey task in backend/tasks.py to transform parsed payload into Google Calendar event and insert into the selected calendarId.
    status: pending
    dependencies:
      - auth-module
      - calendar-picker
  - id: schedule-endpoint
    content: Add POST /schedule to backend/app.py to validate payload and enqueue the push task, returning task_id.
    status: pending
    dependencies:
      - push-task
  - id: ui-submit
    content: Update React UI to submit on Enter (natural mode) to /schedule and hide window on success; show inline error on failure. If no calendar selected, prompt user to pick one first.
    status: pending
    dependencies:
      - schedule-endpoint
  - id: gitignore-secrets
    content: Ignore backend/token.json and backend/credentials.json in .gitignore (and backend/settings.json if we store calendar selection there).
    status: pending
    dependencies:
      - auth-module
---

# Phase 5: Calendar Integration

## Goal

Add Google Calendar integration so submitting an event from the UI triggers a backend `/schedule` call, which enqueues a Huey task to create the event on a **user-selected** Google Calendar.

## Decisions

- **OAuth mode**: `InstalledAppFlow` loopback redirect (starts localhost server, opens browser, auto-saves token)
- **Calendar target**: **user-selected calendarId** (chosen from the user’s calendar list after OAuth)

## Current state we’ll build on

- Flask API in [`backend/app.py`](/Users/felix/Documents/cumo/backend/app.py)
- Huey queue + consumer thread in [`backend/tasks.py`](/Users/felix/Documents/cumo/backend/tasks.py)
- Backend deps already include `google-auth`, `google-auth-oauthlib`, `google-api-python-client` in [`backend/requirements.txt`](/Users/felix/Documents/cumo/backend/requirements.txt)

## Implementation plan

### 1) Add OAuth helper module

Create [`backend/auth.py`](/Users/felix/Documents/cumo/backend/auth.py):

- Read Google OAuth client secrets from a local file (default `backend/credentials.json`, overridable via env var like `CUMO_GOOGLE_CREDENTIALS`).
- Use `google_auth_oauthlib.flow.InstalledAppFlow.run_local_server(...)` to complete auth.
- Save refreshable credentials to `backend/token.json`.
- Expose a helper like `get_calendar_service()` that returns an authenticated `googleapiclient.discovery.build('calendar','v3')` service.

### 2) Add calendar push task

Update [`backend/tasks.py`](/Users/felix/Documents/cumo/backend/tasks.py):

- Add a Huey task `push_to_calendar(event_payload)`.
- Convert your parsed JSON into a Google Calendar event:
- `summary` from `title`
- `start.dateTime` from `datetime`
- `end.dateTime` from `end_time` if present, otherwise default duration (e.g. +60 minutes)
- set `timeZone` (default local timezone; allow override via env var)
- Determine `calendarId` from settings (e.g. `selectedCalendarId`). If not set, return a clear error indicating the user must select a calendar first.
- Call `service.events().insert(calendarId=calendarId, body=...).execute()`.
- Return the created event id/link.

### 3) Add calendar list + selection endpoints

Update [`backend/app.py`](/Users/felix/Documents/cumo/backend/app.py) (and optionally add a tiny settings helper module):

- Add `GET /calendars`:
  - Requires valid OAuth credentials
  - Returns a list from `calendarList.list()` with fields like `{ id, summary, primary }`
- Add settings endpoints:
  - `GET /settings` returns `{ selectedCalendarId }`
  - `POST /settings/calendar` (or `POST /settings`) stores `{ selectedCalendarId }` in a local file (e.g. `backend/settings.json`)

### 4) Add Flask endpoint for scheduling

Update [`backend/app.py`](/Users/felix/Documents/cumo/backend/app.py):

- Add `POST /schedule`:
- Validate JSON body (either accept the parsed structure directly, or accept `{ text }` and call the NLP parser first)
- Enqueue `push_to_calendar` via Huey (e.g. `push_to_calendar(payload)` or `.schedule(...)` depending on how we want retries/delay)
- Return immediately with `{ enqueued: true, task_id }`

### 5) UI calendar picker + submit wiring

Update [`src/App.jsx`](/Users/felix/Documents/cumo/src/App.jsx):

- If `selectedCalendarId` is not set:
  - Fetch `GET /calendars` and render a simple picker (dropdown/list)
  - Persist selection via `POST /settings/calendar`
- On **Enter** in Natural mode:
- If we already have `preview`, submit it to `POST /schedule`.
- Hide the window on success via `window.electron.hideWindow()`.
- Show a small inline error on failure.

### 6) Secrets + artifacts hygiene

Update [`/Users/felix/Documents/cumo/.gitignore`](/Users/felix/Documents/cumo/.gitignore):

- Ignore `backend/token.json`
- Ignore `backend/credentials.json`
- Ignore `backend/settings.json` (stores selectedCalendarId locally)

## Verification

- Run app, complete OAuth (either dedicated endpoint or on first access to `/calendars`)
- Pick a calendar in the UI
- Type: `buy groceries tomorrow at 2pm`
- Press Enter
- Confirm event appears on Google Calendar (selected calendar)

## Notes

- We will **not** show raw JSON in production; Phase 5 focuses on submission + background push.