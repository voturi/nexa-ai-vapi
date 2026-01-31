# Quick Start Guide - Local Development

## Option 1: Pip Install (Recommended for Development)

### Prerequisites
- Python 3.11 or higher
- Redis (for caching)

### Step 1: Install Redis

**macOS (using Homebrew):**
```bash
brew install redis
brew services start redis

# Verify Redis is running
redis-cli ping  # Should return "PONG"
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis

# Verify
redis-cli ping
```

**Windows:**
```bash
# Using WSL2 or download Redis for Windows
# https://redis.io/docs/getting-started/installation/install-redis-on-windows/
```

### Step 2: Set Up Python Environment

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
# OR
.\venv\Scripts\activate   # Windows

# Verify Python version
python --version  # Should be 3.11+
```

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use any editor
```

**Minimum required for local testing:**
```env
# Database (Supabase)
DATABASE_URL=postgresql://postgres:your-password@db.xxxxx.supabase.co:5432/postgres
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# Redis (local)
REDIS_URL=redis://localhost:6379

# VAPI (get from vapi.ai)
VAPI_API_KEY=vapi_sk_xxxxxxxxxxxxx

# Twilio (get from twilio.com)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxx

# Security
ENCRYPTION_KEY=generate-using-command-below
SECRET_KEY=any-random-string-here

# Backend
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

# Environment
ENVIRONMENT=development
```

**Generate Encryption Key:**
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Step 5: Set Up Database

**Option A: Use Supabase Cloud (Recommended for quick start)**
1. Go to https://supabase.com
2. Create a free project
3. Go to Settings → Database
4. Copy the connection string to `DATABASE_URL` in `.env`
5. Copy Project URL and API keys

**Option B: Set up tables manually**
```bash
# TODO: Run Alembic migrations once they're created
alembic upgrade head
```

For now, you can create tables manually in Supabase SQL Editor:
- Go to your Supabase project
- Navigate to SQL Editor
- Run the table creation scripts (will be provided in migration files)

### Step 6: Run the Application

```bash
# Make sure you're in the backend directory with venv activated
cd backend
source venv/bin/activate  # if not already activated

# Run with hot-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or for more detailed logs
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
```

### Step 7: Test the API

Open your browser or use curl:

```bash
# Health check
curl http://localhost:8000/health

# API docs (Swagger UI)
open http://localhost:8000/docs

# ReDoc
open http://localhost:8000/redoc
```

### Development Workflow

1. **Make code changes** - Files update automatically with `--reload`
2. **Check logs** in terminal where uvicorn is running
3. **Test endpoints** at http://localhost:8000/docs
4. **Debug** - Add breakpoints in your IDE, they'll work directly

### Useful Commands

```bash
# Install new dependency
pip install package-name
pip freeze > requirements.txt

# Check Redis is working
redis-cli ping

# View Redis data
redis-cli
> KEYS *
> GET key_name

# Format code
black app/

# Run tests (once created)
pytest

# Type checking
mypy app/
```

---

## Option 2: Docker Compose (For Production-like Testing)

Use Docker when you want to test the full containerized setup.

### Prerequisites
- Docker Desktop
- Docker Compose

### Step 1: Configure Environment

```bash
cd backend
cp .env.example .env
# Edit .env with your credentials
```

### Step 2: Start Services

```bash
# Start all services (backend + Redis)
docker-compose up -d

# View logs
docker-compose logs -f backend

# Check status
docker-compose ps
```

### Step 3: Access the API

- API: http://localhost:8000
- Docs: http://localhost:8000/docs

### Step 4: Rebuild After Changes

```bash
# Rebuild after dependency changes
docker-compose build

# Restart services
docker-compose restart

# Stop all services
docker-compose down
```

### Docker Development Tips

**To see live code changes with Docker:**

The docker-compose.yml already has volume mounts, so changes to `.py` files will trigger reload. But:

```bash
# Rebuild if you change requirements.txt
docker-compose build backend

# View logs in real-time
docker-compose logs -f backend
```

**To run commands inside container:**
```bash
# Open shell in backend container
docker-compose exec backend bash

# Run tests
docker-compose exec backend pytest

# Run migrations
docker-compose exec backend alembic upgrade head
```

---

## Testing Webhooks Locally

VAPI needs to send webhooks to your backend. Since you're on localhost, you need a tunnel:

### Using ngrok (Recommended)

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com/download

# Start tunnel to your local server
ngrok http 8000

# You'll get a URL like: https://abc123.ngrok.io
# Use this in VAPI webhook configuration:
# https://abc123.ngrok.io/webhooks/vapi/call-started
```

### Update VAPI Assistant Webhooks

1. Go to VAPI dashboard
2. Edit your assistant
3. Set webhook URLs:
   - Call Started: `https://your-ngrok-url.ngrok.io/webhooks/vapi/call-started`
   - Function Call: `https://your-ngrok-url.ngrok.io/webhooks/vapi/function-call`
   - Call Ended: `https://your-ngrok-url.ngrok.io/webhooks/vapi/call-ended`

---

## Quick Comparison

| Feature | Pip Install | Docker |
|---------|-------------|--------|
| Setup time | 5 min | 2 min |
| Hot reload | ✅ Instant | ✅ With volumes |
| Debugging | ✅ Excellent | ⚠️ Harder |
| IDE integration | ✅ Perfect | ⚠️ Limited |
| Iteration speed | ✅ Fast | ⚠️ Slower |
| Production parity | ⚠️ Good | ✅ Excellent |
| Resource usage | ✅ Light | ⚠️ Heavy |

## Recommendation

**For active development:** Use **pip install**
- Faster iteration
- Better debugging experience
- Easier to see what's happening

**For testing deployments:** Use **Docker**
- Test containerization
- Ensure production compatibility
- Share exact environment with team

---

## Troubleshooting

### Redis Connection Error
```bash
# Check if Redis is running
redis-cli ping

# Start Redis (macOS)
brew services start redis

# Start Redis (Linux)
sudo systemctl start redis
```

### Port Already in Use
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn app.main:app --reload --port 8001
```

### Import Errors
```bash
# Make sure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Supabase Connection Error
- Check DATABASE_URL is correct
- Verify Supabase project is active
- Check if IP is whitelisted (Supabase → Settings → Database → Connection Pooling)

### Environment Variables Not Loading
```bash
# Check .env file exists
ls -la .env

# Verify it's in the backend directory
pwd  # Should show .../backend

# Print environment variable to debug
python -c "from app.core.config import settings; print(settings.DATABASE_URL)"
```

---

## Next Steps After Setup

1. ✅ Verify health endpoint works
2. ✅ Explore API docs at /docs
3. ✅ Set up ngrok for webhook testing
4. ✅ Create a test tenant
5. ✅ Configure VAPI assistant
6. ✅ Make a test call!
