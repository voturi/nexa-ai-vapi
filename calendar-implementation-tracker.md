# Google Calendar & OAuth Integration — Implementation Tracker

**Created**: March 17, 2026
**Branch**: `feature/google-calendar-integration`
**Status**: Phases 1-3 Implemented + E2E Tested (March 26, 2026)

---

## What Was Built

### Phase 1: Google Calendar Client
- **File**: `app/integrations/google_calendar_client.py`
- FreeBusy API for availability checks, event create/cancel
- Automatic token refresh detection + credential passback

### Phase 2: OAuth Flow & Credential Management
- **File**: `app/services/integration_service.py` — encrypt/store/retrieve/update/disconnect
- **File**: `app/api/v1/endpoints/integrations.py` — 6 endpoints:
  - `POST /api/v1/integrations/google-calendar/start` — start OAuth (Supabase JWT auth)
  - `GET /api/v1/integrations/google-calendar/callback` — handle Google redirect
  - `GET /api/v1/integrations/google-calendar/status` — connection status
  - `DELETE /api/v1/integrations/google-calendar/disconnect` — remove integration
  - `GET /api/v1/integrations/google-calendar/calendars` — list available calendars
  - `PUT /api/v1/integrations/google-calendar/config` — select calendar_id

### Phase 3: VAPI Tool Handler Wiring
- **File**: `app/services/vapi_service.py` — modified:
  - `check_availability` → queries real Google Calendar, falls back to mock slots
  - `create_booking` → creates Google Calendar event + stores `calendar_event_id`
  - Token refresh persisted transparently after each API call
  - Passes tenant timezone to availability checks

### Route Registration
- **File**: `app/api/v1/api.py` — added integrations router

---

## Bugs Fixed (March 26, 2026)

### 1. Frontend/Backend Endpoint Mismatch
- Frontend called `POST /start`, backend had `GET /authorize`
- **Fix**: Changed backend to `POST /google-calendar/start`

### 2. Auth Mismatch
- Integration endpoints used API key auth (`get_current_tenant`), frontend sends Supabase JWT
- **Fix**: Switched all integration endpoints to `get_current_user_tenant` (Supabase JWT auth)

### 3. Callback Redirect URL
- Backend redirected to `/integrations/google-calendar?success=true` (non-existent route)
- **Fix**: Redirects to `/auth/google-calendar/callback?success=true` (matches frontend route)

### 4. Frontend Callback Double-Handling
- Callback page tried to call backend callback via AJAX, but backend redirects the browser directly
- **Fix**: Simplified callback page to read `?success=true` or `?error=` from URL params

### 5. FreeBusy Timezone Bug
- Times were sent with `"Z"` (UTC) suffix, so FreeBusy queried 9AM–5PM UTC instead of local time
- Google returns busy periods in UTC — these were compared to local naive datetimes without conversion
- **Fix**: Send RFC3339 timestamps with timezone offset, set `timeZone` param, convert UTC busy periods to local time via `zoneinfo`

---

## E2E Test Results (March 26, 2026)

Tested with real Google account (`nexa247.ai@gmail.com`) against Mike's Plumbing tenant.

| Test | Result |
|------|--------|
| OAuth flow (frontend → Google → callback → stored) | Pass |
| Credentials encrypted & stored in DB | Pass |
| List calendars | Pass — primary + Holidays in Australia |
| Check availability (empty day) | Pass — 8 x 1-hour slots (9AM–4PM) |
| Create calendar event | Pass — confirmed status, correct timezone |
| FreeBusy reflects booked slots | Pass — 10AM blocked, 7 slots returned |
| Cancel event | Pass |
| Token refresh detection | Pass |

---

## Remaining Work

### Phase 4: Dynamic Context Enhancement
- [ ] Enrich system prompt with real-time availability on call start
- [ ] Today's remaining slots, next available, open/closed status
- [ ] Cache in Redis with 5-min TTL per tenant

### Phase 5: Token Lifecycle & Reliability
- [ ] Background job for proactive token refresh
- [ ] Handle Google token revocation gracefully
- [ ] Retry logic with exponential backoff
- [ ] Invalidate Redis availability cache on booking creation

### Testing
- [x] Integration test: OAuth flow end-to-end (manual, March 26)
- [x] E2E test: availability → booking → calendar event (manual, March 26)
- [ ] Unit tests for GoogleCalendarClient (mocked Google API)
- [ ] Unit tests for IntegrationService (encrypt/decrypt)

---

**Last Updated**: March 26, 2026
