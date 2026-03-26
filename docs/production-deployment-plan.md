# Production Deployment Plan — Nexa Receptionist Systems

**Date**: March 27, 2026
**Backend**: Railway (Python/FastAPI)
**Frontend**: Vercel (React/Vite)
**Database**: Supabase (managed PostgreSQL)
**Redis**: Railway (managed Redis plugin)

---

## Architecture Overview

```
                    ┌─────────────┐
                    │   Vercel     │
                    │  (Frontend)  │
                    │  React/Vite  │
                    └──────┬──────┘
                           │ HTTPS
                           ▼
┌──────────┐       ┌──────────────┐       ┌──────────────┐
│  VAPI    │──────▶│   Railway    │──────▶│  Supabase    │
│  Webhooks│  HTTPS│  (Backend)   │  PG   │  PostgreSQL  │
└──────────┘       │  FastAPI     │       └──────────────┘
                   │  + Redis     │
┌──────────┐       │              │       ┌──────────────┐
│  Twilio  │──────▶│              │──────▶│  Google      │
│          │       └──────────────┘  OAuth│  Calendar    │
└──────────┘                              └──────────────┘
```

---

## Phase 1: Railway Backend Setup

### 1.1 Create Railway Project

1. Create new project at [railway.app](https://railway.app)
2. Connect the GitHub repo (`voturi/nexa-ai-vapi`)
3. Set root directory to `/` (the backend is at repo root)
4. Railway auto-detects Python via `requirements.txt`

### 1.2 Add Redis Plugin

1. In the Railway project dashboard, click **+ New** → **Database** → **Redis**
2. Railway provisions a managed Redis instance and exposes `REDIS_URL` automatically
3. Link the Redis service to the backend service

### 1.3 Configure Build & Start

| Setting | Value |
|---------|-------|
| Build Command | `pip install -r requirements.txt` |
| Start Command | `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |
| Restart Policy | On failure |

> **Note**: Railway sets `$PORT` dynamically. Uvicorn must bind to it.

### 1.4 Environment Variables

Set these in Railway's **Variables** tab:

#### Database & Auth
```
DATABASE_URL=postgresql://postgres.xxxxx:password@aws-0-region.pooler.supabase.com:5432/postgres
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
SUPABASE_ANON_KEY=eyJ...
SUPABASE_JWT_SECRET=<from Supabase dashboard → Settings → API → JWT Secret>
```

#### Core Services
```
VAPI_API_KEY=vapi_sk_...
VAPI_BASE_URL=https://api.vapi.ai
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
```

#### Security (generate fresh for production)
```
ENCRYPTION_KEY=<generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(64))">
```

#### URLs (update after both services are deployed)
```
ENVIRONMENT=production
BACKEND_URL=https://<railway-app>.up.railway.app
FRONTEND_URL=https://<vercel-app>.vercel.app
GOOGLE_OAUTH_REDIRECT_URI=https://<railway-app>.up.railway.app/api/v1/integrations/google-calendar/callback
```

#### Google Calendar
```
GOOGLE_OAUTH_CLIENT_ID=<from Google Cloud Console>
GOOGLE_OAUTH_CLIENT_SECRET=<from Google Cloud Console>
```

#### Monitoring (optional but recommended)
```
SENTRY_DSN=https://...@sentry.io/...
LOG_LEVEL=INFO
```

### 1.5 Database Migrations

Migrations run automatically on each deploy via the start command (`alembic upgrade head && uvicorn ...`). For the first deploy:

1. Verify `DATABASE_URL` uses the **direct connection** string (not the pooler) for migrations
2. Railway's start command runs migrations before the server starts
3. If migration fails, the deploy fails — preventing broken deploys

### 1.6 Google OAuth — Update Redirect URI

After Railway assigns a URL:

1. Go to [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials)
2. Edit the OAuth client
3. Add authorized redirect URI: `https://<railway-app>.up.railway.app/api/v1/integrations/google-calendar/callback`
4. Update `GOOGLE_OAUTH_REDIRECT_URI` in Railway variables

---

## Phase 2: Vercel Frontend Setup

### 2.1 Create Vercel Project

1. Import the same GitHub repo at [vercel.com/new](https://vercel.com/new)
2. Set **Root Directory** to `frontend`
3. Vercel auto-detects Vite

### 2.2 Configure Build

| Setting | Value |
|---------|-------|
| Framework Preset | Vite |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Install Command | `npm install` |
| Node Version | 20.x |

### 2.3 Environment Variables

Set in Vercel's **Settings → Environment Variables**:

```
VITE_API_URL=https://<railway-app>.up.railway.app
VITE_SUPABASE_URL=https://xxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
VITE_SENTRY_DSN=https://...@sentry.io/...
```

> **Important**: `VITE_` prefix is required — Vite only exposes prefixed vars to the client bundle.

### 2.4 Rewrites (API Proxy Removal)

In development, Vite proxies `/api` requests to the backend. In production, the frontend calls the backend directly via `VITE_API_URL`. No Vercel rewrites needed — the frontend `api.ts` already uses `API_BASE_URL` for all requests.

### 2.5 Custom Domain (Optional)

1. Add a custom domain in Vercel (e.g., `app.nexareceptionist.com.au`)
2. Update `FRONTEND_URL` in Railway to match
3. Update Supabase Auth → URL Configuration → Site URL to the custom domain

---

## Phase 3: VAPI & Twilio Configuration

### 3.1 Update VAPI Webhook URLs

In the VAPI dashboard, update the assistant's **Server URL** to:

```
https://<railway-app>.up.railway.app/webhooks/vapi/function-call
```

VAPI sends all webhook types (call-started, tool-calls, end-of-call-report) to this single `serverUrl`. The backend routes them based on `message.type`.

### 3.2 Update Twilio Webhook (if applicable)

If Twilio is configured to forward calls via webhook:
- Voice URL: `https://<railway-app>.up.railway.app/webhooks/twilio/voice`

### 3.3 Verify Webhooks Are Reachable

```bash
# From your local machine
curl -s https://<railway-app>.up.railway.app/health
# Expected: {"status": "healthy", "version": "1.0.0"}

curl -s -X POST https://<railway-app>.up.railway.app/webhooks/vapi/debug \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

---

## Phase 4: Supabase Configuration

### 4.1 Auth Settings

In Supabase Dashboard → Authentication → URL Configuration:

| Setting | Value |
|---------|-------|
| Site URL | `https://<vercel-app>.vercel.app` |
| Redirect URLs | `https://<vercel-app>.vercel.app/auth/google-calendar/callback` |

### 4.2 Connection Pooling

Supabase provides two connection strings:
- **Direct**: `postgresql://postgres.xxx:password@db.xxx.supabase.co:5432/postgres` — use for migrations
- **Pooler**: `postgresql://postgres.xxx:password@aws-0-region.pooler.supabase.com:6543/postgres` — use for the app

For Railway, use the **pooler** connection in `DATABASE_URL` for runtime, but ensure `alembic` can handle the async driver conversion (`postgresql://` → `postgresql+asyncpg://`).

### 4.3 Row Level Security

Review RLS policies on tables. The backend uses `SUPABASE_SERVICE_KEY` (service role) which bypasses RLS. This is fine for the backend, but ensure the anon key cannot access sensitive data directly.

---

## Phase 5: Post-Deployment Verification

### 5.1 Smoke Test Checklist

Run these in order after both services are live:

```
[ ] 1. Backend health check responds
       curl https://<railway>.up.railway.app/health

[ ] 2. Frontend loads login page
       Open https://<vercel>.vercel.app/login

[ ] 3. User can sign in
       Login with mike@mikesplumbing.com.au / Test1234!

[ ] 4. Dashboard loads with real data
       Stats, recent calls, upcoming bookings render

[ ] 5. Google Calendar OAuth flow works
       Settings → Connect → Google sign-in → success redirect

[ ] 6. VAPI webhook responds
       Make a test call to the Twilio number

[ ] 7. check_availability returns real calendar data
       Verify during test call or via webhook test

[ ] 8. create_booking creates Google Calendar event
       Book a slot during test call, verify event in Google Calendar

[ ] 9. Call record appears in dashboard
       After test call, refresh dashboard — call should appear
```

### 5.2 Monitoring Setup

| Tool | Purpose | Setup |
|------|---------|-------|
| Sentry | Error tracking (backend + frontend) | Set `SENTRY_DSN` in both Railway and Vercel |
| Railway Metrics | CPU, memory, request count | Built-in, no config needed |
| Vercel Analytics | Frontend performance | Enable in Vercel dashboard |
| Supabase Dashboard | DB health, connection count | Built-in |

---

## Environment Variable Reference

### Backend (Railway)

| Variable | Required | Example |
|----------|----------|---------|
| `DATABASE_URL` | Yes | `postgresql://postgres.xxx:pw@pooler.supabase.com:6543/postgres` |
| `SUPABASE_URL` | Yes | `https://xxx.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Yes | `eyJ...` |
| `SUPABASE_ANON_KEY` | Yes | `eyJ...` |
| `SUPABASE_JWT_SECRET` | Yes | `base64-encoded secret` |
| `REDIS_URL` | Yes | Auto-set by Railway Redis plugin |
| `VAPI_API_KEY` | Yes | `vapi_sk_...` |
| `TWILIO_ACCOUNT_SID` | Yes | `AC...` |
| `TWILIO_AUTH_TOKEN` | Yes | Secret |
| `ENCRYPTION_KEY` | Yes | Fernet key (generate fresh) |
| `SECRET_KEY` | Yes | Random 64-char string |
| `ENVIRONMENT` | Yes | `production` |
| `BACKEND_URL` | Yes | `https://<railway>.up.railway.app` |
| `FRONTEND_URL` | Yes | `https://<vercel>.vercel.app` |
| `GOOGLE_OAUTH_CLIENT_ID` | Yes | `xxx.apps.googleusercontent.com` |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Yes | `GOCSPX-...` |
| `GOOGLE_OAUTH_REDIRECT_URI` | Yes | `https://<railway>.up.railway.app/api/v1/integrations/google-calendar/callback` |
| `SENTRY_DSN` | No | `https://...@sentry.io/...` |
| `LOG_LEVEL` | No | `INFO` |

### Frontend (Vercel)

| Variable | Required | Example |
|----------|----------|---------|
| `VITE_API_URL` | Yes | `https://<railway>.up.railway.app` |
| `VITE_SUPABASE_URL` | Yes | `https://xxx.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | Yes | `eyJ...` |
| `VITE_SENTRY_DSN` | No | `https://...@sentry.io/...` |

---

## Rollback Plan

| Scenario | Action |
|----------|--------|
| Bad backend deploy | Railway → Deployments → click previous deploy → **Rollback** |
| Bad frontend deploy | Vercel → Deployments → click previous deploy → **Promote to Production** |
| Bad migration | SSH into Railway, run `alembic downgrade -1` |
| Redis data corruption | Railway Redis → **Flush** (cache is ephemeral, rebuilds on next call) |
| Google OAuth broken | Revert `GOOGLE_OAUTH_REDIRECT_URI` to previous value |

---

## Cost Estimate

| Service | Tier | Estimated Cost |
|---------|------|---------------|
| Railway (backend) | Pro | ~$5-20/mo (usage-based) |
| Railway (Redis) | Plugin | ~$5-10/mo |
| Vercel (frontend) | Pro | $20/mo (or free tier for low traffic) |
| Supabase (database) | Free/Pro | Free tier sufficient initially, Pro $25/mo |
| VAPI | Pay-per-call | ~$0.05-0.10/min |
| Twilio | Pay-per-call | ~$0.02/min + $1/mo per number |
| Google Calendar API | Free | Free (within quota limits) |
| Sentry | Free tier | Free (5k errors/mo) |
| **Total** | | **~$30-75/mo** + per-call costs |

---

## Security Checklist

```
[ ] Generate fresh ENCRYPTION_KEY and SECRET_KEY for production
[ ] Never reuse development keys
[ ] Verify .env is in .gitignore (already is)
[ ] CORS allows only FRONTEND_URL origin
[ ] HTTPS enforced on all endpoints (Railway and Vercel handle this)
[ ] Webhook signature verification enabled in production
[ ] Supabase RLS policies reviewed
[ ] Google OAuth consent screen moved from "Testing" to "Production" (requires verification)
[ ] API keys rotated from any values committed during development
```

---

## Deployment Order

1. **Railway backend** — deploy first, get the URL
2. **Update env vars** — set `BACKEND_URL` in Railway, update Google OAuth redirect
3. **Vercel frontend** — deploy with `VITE_API_URL` pointing to Railway
4. **Update Railway** — set `FRONTEND_URL` to Vercel URL (for CORS)
5. **Supabase** — update Site URL and redirect URLs
6. **VAPI** — update server URL to Railway webhook endpoint
7. **Google Cloud** — add production redirect URI
8. **Smoke test** — run the full checklist above
