# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Nexa Receptionist Systems** - Multi-tenant SaaS platform providing AI-powered voice receptionist services for businesses across various verticals (tradies, hair salons, medical, SMBs, etc.).

**Tech Stack**: FastAPI (Python 3.11+), Supabase (PostgreSQL), Redis, VAPI, Twilio, Anthropic Claude

## Development Commands

### Local Development
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run with Docker
docker-compose up -d
```

### Database Operations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_tenant_service.py

# Run tests matching pattern
pytest -k "test_create"
```

### Code Quality
```bash
# Format code (auto-fix)
black app/

# Sort imports (auto-fix)
isort app/

# Lint code
flake8 app/

# Type checking
mypy app/
```

## Architecture

### Multi-Tenancy Model

**Critical Pattern**: One VAPI account → Multiple VAPI Assistants (one per tenant)

Each tenant gets:
- Unique VAPI Assistant ID
- Unique Twilio phone number
- Unique webhook secret
- Unique API key
- Tenant-specific credentials (encrypted)
- Vertical-specific configuration

**Tenant Isolation**: VAPI webhooks include `tenant_id` in metadata, used to route all operations to correct tenant context.

### Skills System

Skills are **markdown files** in `/skills` directory that define:
- Conversation patterns by vertical
- Integration workflows
- Universal best practices

**Skills Loading Flow**:
1. Call starts → webhook receives `tenant_id`
2. Load tenant config from database
3. Determine vertical and enabled integrations
4. Load relevant skills: `vertical skills + integration skills + core skills`
5. Build system prompt with skills + tenant config + dynamic context
6. Return enhanced prompt to VAPI

**Important**: Skills are cached in memory via `@lru_cache`. Changes to skill files require application restart in production.

### Webhook Flow

```
Incoming Call → Twilio → VAPI Assistant
                           ↓
VAPI webhooks to backend:
1. /webhooks/vapi/call-started
   - Load tenant config
   - Build system prompt with skills
   - Return enhanced context to VAPI

2. /webhooks/vapi/function-call
   - Extract tenant_id from metadata
   - Load tenant-specific credentials
   - Execute integration (calendar, CRM, etc.)
   - Return result to VAPI

3. /webhooks/vapi/call-ended
   - Process transcript
   - Save call record
   - Update analytics
   - Trigger any post-call workflows
```

### Database Schema

**Primary Tables**:
- `tenants`: Business accounts
- `calls`: Call records and transcripts
- `bookings`: Scheduled appointments
- `leads`: Qualified leads
- `tenant_integrations`: Encrypted credentials

**Supabase Usage**:
- PostgreSQL for all relational data
- Use SQLAlchemy for ORM
- Use Supabase client for auth (if needed) and storage
- Alembic for migrations

**Redis Usage**:
- Cache tenant configs (hot path)
- Cache caller context during calls
- Store temporary availability data
- Rate limiting

### Security

**Credential Encryption**:
- All tenant credentials encrypted with Fernet (symmetric encryption)
- Encryption key stored in environment variable
- Credentials stored as binary in `tenant_integrations` table
- Use `CredentialsManager` class for all encrypt/decrypt operations

**Webhook Security**:
- VAPI sends `X-VAPI-Signature` header
- Verify using HMAC-SHA256 with tenant's webhook_secret
- Reject requests with invalid signatures

**API Authentication**:
- Tenants use Bearer token (API key)
- Stored in `tenants.api_key` column
- Verified via `get_current_tenant` dependency

## Critical Patterns

### Service Layer Pattern

All business logic in `/app/services`. Controllers (`/app/api`) should be thin:

```python
# Good - Controller delegates to service
@router.post("/bookings")
async def create_booking(
    booking_data: BookingCreate,
    db: AsyncSession = Depends(get_db),
    tenant = Depends(get_current_tenant),
):
    service = BookingService(db)
    return await service.create(tenant.id, booking_data)

# Bad - Business logic in controller
@router.post("/bookings")
async def create_booking(...):
    # Complex validation, integration calls, etc.
```

### Integration Pattern

Each integration has:
1. Client class in `/app/integrations/{integration_name}.py`
2. Skill files in `/skills/integrations/{integration_name}/`
3. Tool definitions registered with VAPI

**Integration Client Structure**:
```python
class GoogleCalendarClient:
    def __init__(self, credentials: dict):
        self.credentials = credentials
        self.service = self._build_service()

    async def check_availability(self, service_id, date):
        # Implementation

    async def create_booking(self, booking_data):
        # Implementation
```

### Async/Await Pattern

**Always use async/await** for:
- Database operations
- External API calls
- Redis operations
- File I/O (if async library available)

**Use sync only for**:
- Pure computation
- In-memory operations
- Skill file loading (cached)

## Common Development Workflows

### Adding a New Vertical

1. Create skill directory: `/skills/verticals/{vertical_name}/`
2. Add `CONVERSATION_STYLE.md` and vertical-specific skills
3. Update tenant model if needed (add to vertical enum/choices)
4. Test with skills engine: `skills_engine.get_skills_for_vertical(vertical_name)`

### Adding a New Integration

1. Create client class: `/app/integrations/{integration}_client.py`
2. Add skill files: `/skills/integrations/{integration}/`
3. Add credentials schema to `tenant_integrations` config
4. Register tools with VAPI assistant
5. Handle tool execution in `/app/webhooks/vapi.py`
6. Add OAuth flow if needed: `/app/api/v1/endpoints/integrations.py`

### Webhook Development

When modifying webhook handlers:
1. Extract `tenant_id` from `metadata` first
2. Load tenant config (with error handling)
3. Verify webhook signature (production only)
4. Process event with tenant context
5. Return appropriate response format for VAPI
6. Log structured data for debugging

**VAPI expects specific response formats** - check VAPI docs for exact schema.

## Environment Setup

### Required Environment Variables

**Database**:
- `DATABASE_URL`: PostgreSQL connection string (from Supabase)
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_SERVICE_KEY`: Service role key (not anon key)
- `REDIS_URL`: Redis connection string

**External Services**:
- `VAPI_API_KEY`: VAPI API key (starts with `vapi_sk_`)
- `TWILIO_ACCOUNT_SID`: Twilio account SID
- `TWILIO_AUTH_TOKEN`: Twilio auth token

**Security**:
- `ENCRYPTION_KEY`: Base64-encoded Fernet key
- `SECRET_KEY`: JWT signing key

**Integrations** (optional):
- `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`
- `HUBSPOT_CLIENT_ID`, `HUBSPOT_CLIENT_SECRET`
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`

### Generating Encryption Key

```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())  # Put this in ENCRYPTION_KEY env var
```

## Testing Strategy

### Unit Tests
- Test services in isolation
- Mock database and external APIs
- Focus on business logic
- Location: `/tests/unit/`

### Integration Tests
- Test API endpoints end-to-end
- Use test database
- Mock external services (VAPI, Twilio)
- Location: `/tests/integration/`

### E2E Tests
- Test complete call flow
- Use VAPI test numbers
- Verify webhook handling
- Location: `/tests/e2e/`

## Important Files

- `/app/main.py`: FastAPI application entry point
- `/app/core/config.py`: Configuration and settings
- `/app/core/database.py`: Database connection management
- `/app/core/security.py`: Authentication and encryption utilities
- `/app/services/skills_engine.py`: Skills loading and prompt building
- `/app/webhooks/vapi.py`: VAPI webhook handlers
- `/docs/multi-tenant-voice-ai-architecture.md`: Full architecture documentation

## Debugging

### Common Issues

**Skills not loading**:
- Check `SKILLS_BASE_PATH` environment variable
- Verify skill files exist and are readable
- Check for syntax errors in markdown files
- Remember: skills are cached, restart app after changes

**Webhook signature mismatch**:
- Verify `webhook_secret` in database matches VAPI dashboard
- Check body is not modified before verification
- Ensure using raw body bytes, not parsed JSON

**Integration auth failures**:
- Check credentials are properly encrypted/decrypted
- Verify OAuth tokens haven't expired
- Check integration config in `tenant_integrations` table
- Test credentials with integration's API directly

**Database connection issues**:
- Verify Supabase connection string format
- Check if using async driver (`asyncpg`)
- Ensure connection pooling settings are appropriate

### Logging

Use structured logging:
```python
import structlog
logger = structlog.get_logger()

logger.info(
    "booking_created",
    tenant_id=str(tenant.id),
    booking_id=str(booking.id),
    service=booking.service_id
)
```

**Log Levels**:
- `DEBUG`: Development only, verbose
- `INFO`: Important events (bookings, calls)
- `WARNING`: Recoverable issues
- `ERROR`: Failures requiring attention

## Performance Considerations

1. **Cache tenant configs**: Load once per call, store in Redis
2. **Skills loading**: Cached via `@lru_cache`, cleared on app restart
3. **Database queries**: Use async, add indexes on foreign keys
4. **Webhook responses**: Must be fast (<1s), defer heavy processing
5. **Integration calls**: Use timeouts, implement retries with exponential backoff

## Deployment

**Production checklist**:
- [ ] Set `ENVIRONMENT=production` in env vars
- [ ] Use production Supabase project
- [ ] Enable webhook signature verification
- [ ] Configure proper logging level
- [ ] Set up monitoring and alerting
- [ ] Use managed Redis (not docker-compose)
- [ ] Enable HTTPS for all webhook endpoints
- [ ] Set proper CORS origins
- [ ] Run database migrations before deployment
- [ ] Test webhook endpoints are publicly accessible

## Additional Resources

- Architecture document: `/docs/multi-tenant-voice-ai-architecture.md`
- VAPI documentation: https://docs.vapi.ai
- Supabase docs: https://supabase.com/docs
- FastAPI docs: https://fastapi.tiangolo.com
