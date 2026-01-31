# Voice AI Receptionist - Backend

Multi-tenant SaaS platform providing AI-powered voice receptionist services using VAPI, Twilio, and Anthropic Claude.

## Quick Start

### Prerequisites
- Python 3.11+
- Supabase account
- Redis
- VAPI account
- Twilio account

### Installation

1. Clone and navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the server:
```bash
uvicorn app.main:app --reload
```

API will be available at http://localhost:8000

## Docker Setup

```bash
docker-compose up -d
```

## Project Structure

```
backend/
├── app/
│   ├── api/              # API routes
│   ├── core/             # Core config, database, security
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic
│   ├── integrations/     # External integrations
│   ├── webhooks/         # Webhook handlers
│   └── utils/            # Utilities
├── skills/               # Skills directory (markdown files)
│   ├── verticals/        # Vertical-specific skills
│   ├── integrations/     # Integration workflows
│   └── core/             # Universal best practices
├── tests/                # Tests
├── alembic/              # Database migrations
└── scripts/              # Utility scripts
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

### Running Tests
```bash
pytest
```

### Code Quality
```bash
# Format code
black app/

# Sort imports
isort app/

# Lint
flake8 app/

# Type checking
mypy app/
```

### Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback:
```bash
alembic downgrade -1
```

## Architecture

See `/docs/multi-tenant-voice-ai-architecture.md` for detailed architecture documentation.

### Key Components

1. **Multi-Tenancy**: One VAPI account, multiple assistants (one per tenant)
2. **Skills System**: Modular instruction sets for verticals and integrations
3. **Webhook Handlers**: Process VAPI callbacks for call events
4. **Integrations**: Google Calendar, HubSpot, Stripe, etc.
5. **Security**: Encrypted credential storage, webhook verification

## Environment Variables

See `.env.example` for all required environment variables.

Critical variables:
- `DATABASE_URL`: PostgreSQL connection (Supabase)
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_SERVICE_KEY`: Supabase service role key
- `VAPI_API_KEY`: VAPI API key
- `TWILIO_ACCOUNT_SID`: Twilio account SID
- `ENCRYPTION_KEY`: Fernet encryption key for credentials

## Skills

Skills are markdown files that define conversation patterns and workflows. Located in `/skills`:

- **verticals/**: Industry-specific conversation styles
- **integrations/**: Integration-specific workflows
- **core/**: Universal best practices

## License

Proprietary
