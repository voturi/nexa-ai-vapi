# Quick Reference Guide

## Starting the Application

```bash
# Activate virtual environment
source venv/bin/activate

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Current Setup

### Phone Number
- **Number**: +61255644466
- **Phone ID**: `0136cdb1-1eae-41e9-a695-dea2c28ebe60`
- **Configuration**: Multi-tenant mode (no pre-assigned assistant)

### Active Tenant
- **Business**: Mike's Plumbing Services
- **Tenant ID**: `2ad294ed-0d2c-4259-a7fd-300d7989efc8`
- **Vertical**: tradies

## Common Commands

### Check System Status
```bash
# Check tenants
python test/debug_scripts/check_tenants.py

# Check phone configuration
python test/debug_scripts/check_phone_status.py

# Verify services
python test/debug_scripts/verify_services.py
```

### Database Operations
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Testing
```bash
# Call the number
+61255644466

# Test phrases:
- "What services do you offer?"
- "Check availability for tomorrow"
- "Book me for 10 AM"
```

## Key URLs

### Webhooks
- **Call Started**: `{BACKEND_URL}/webhooks/vapi/call-started`
- **Function Call**: `{BACKEND_URL}/webhooks/vapi/function-call`
- **Call Ended**: `{BACKEND_URL}/webhooks/vapi/call-ended`

### API Endpoints
- **Health**: `GET /health`
- **Tenants**: `GET /api/v1/tenants`
- **Create Tenant**: `POST /api/v1/tenants`

## Architecture Flow

```
Call → VAPI → assistant-request webhook
              ↓
         Backend cache (<1ms)
              ↓
         Returns assistant config
              ↓
         Call proceeds with AI
              ↓
         Tool calls → function-call webhook
              ↓
         Execute & return result
```

## Important Files

### Core
- `app/main.py` - App entry, cache warming
- `app/webhooks/vapi.py` - VAPI webhooks
- `app/services/vapi_service.py` - VAPI logic
- `app/services/assistant_cache.py` - In-memory cache

### Configuration
- `.env` - Environment variables
- `app/core/config.py` - Settings
- `skills/` - Markdown skill files

### Documentation
- `IMPLEMENTATION_SUMMARY.md` - Full implementation details
- `QUICK_REFERENCE.md` - This file
- `test/debug_scripts/README.md` - Debug tools
- `docs/vap-api.md` - VAPI API examples

## Troubleshooting

### Call not connecting?
```bash
# 1. Check phone config
python test/debug_scripts/check_phone_status.py

# 2. Check backend is running
curl http://localhost:8000/health

# 3. Check logs
# Look for: webhook_call_started_cache_hit
```

### Tools not working?
```bash
# Check logs for:
# - message_type=tool-calls (good)
# - message_type=speech-update (ignored, normal)
# - function_call_completed (success)
```

### Cache issues?
```bash
# Restart server to warm cache
# Check startup logs for:
# - "Warming up assistant cache..."
# - "Assistant cache warmed and ready!"
```

## Log Patterns

### ✅ Success
```
[info] tenant_identified_by_phone_cache
[info] webhook_call_started_cache_hit
[info] webhook_call_started_success
[info] function_call_received function_name=check_availability
[info] function_call_completed success=True
```

### ⚠️ Normal (ignored webhooks)
```
[debug] webhook_serverurl_ignored message_type=speech-update
```

### ❌ Errors
```
[error] webhook_call_started_missing_tenant_id
[error] function_call_failed
[error] no_tool_calls_in_message
```

## Environment Variables Checklist

Required:
- [x] `DATABASE_URL`
- [x] `VAPI_API_KEY`
- [x] `BACKEND_URL`
- [x] `TWILIO_ACCOUNT_SID`
- [x] `TWILIO_AUTH_TOKEN`
- [x] `ENCRYPTION_KEY`
- [x] `SECRET_KEY`

Optional:
- [ ] `SUPABASE_URL`
- [ ] `SUPABASE_SERVICE_KEY`
- [ ] `REDIS_URL`

## Quick Diagnostics

### Is everything working?
1. ✅ `python test/debug_scripts/check_phone_status.py` shows multi-tenant mode
2. ✅ `python test/debug_scripts/check_tenants.py` shows Mike's Plumbing
3. ✅ Server starts without errors
4. ✅ Call connects and AI responds
5. ✅ Tool calls execute successfully

### Performance Check
- Cache hit response: <1ms
- Cache miss response: <100ms
- Tool execution: varies by function

## Adding a New Tenant (Manual)

1. Create tenant in database:
```python
from app.services.tenant_service import TenantService
tenant = await tenant_service.create({
    "business_name": "New Business",
    "vertical": "tradies",
    # ... other fields
})
```

2. Import phone number in VAPI dashboard

3. Update `app/main.py` lifespan to add phone mapping:
```python
assistant_cache.set_phone_mapping(
    "new-phone-id",
    str(tenant.id)
)
```

4. Restart server

## Support

For issues:
1. Check `IMPLEMENTATION_SUMMARY.md` for detailed troubleshooting
2. Review logs in terminal where uvicorn is running
3. Use debug scripts in `test/debug_scripts/`
4. Check VAPI dashboard for webhook delivery status

---

**Last Updated**: February 1, 2026
