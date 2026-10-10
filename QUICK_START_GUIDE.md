# Stock Analysis Platform - Quick Start Guide

## Current Status: Epic 1 Complete ✅, Story 2.1 Complete ✅

### What's Implemented

**Epic 1: Core Backend Infrastructure** (Complete)
- ✅ Story 1.1: FastAPI + LangGraph agent with streaming
- ✅ Story 1.2: Stock price tool (yfinance)
- ✅ Story 1.3: Balance sheet tool
- ✅ Story 1.4: Historical price tool
- ✅ Story 1.5: Company logo tool
- ✅ Story 1.6: PostgreSQL + Docker setup
- ✅ Story 1.7: Redis caching layer (60s for prices, 24h for static data)
- ✅ Story 1.8: Logging enhancement (correlation IDs, structured logs)

**Epic 2: RAG with pgvector + LangCache** (In Progress)
- ✅ Story 2.1: pgvector setup and integration
- ⏳ Story 2.2: OpenAI Embedding Service + LangCache (NEXT)
- ⏳ Story 2.3: Context storage
- ⏳ Story 2.4: Context retrieval
- ⏳ Story 2.5: Integration into chat endpoint
- ⏳ Story 2.6: Performance monitoring
- ⏳ Story 2.7: Quality testing & tuning

## Running the Application

### Prerequisites
- Docker Desktop installed and running
- WSL2 (Windows) or native Linux/Mac
- OpenAI API key

### Start All Services
```bash
cd /mnt/c/Users/mitsi/projects/stockanalysis

# Start everything
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f
```

### Access Points
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8888
- **Backend Docs**: http://localhost:8888/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### Stop Services
```bash
# Stop (keeps data)
docker compose down

# Stop and remove data (fresh start)
docker compose down -v
```

## Environment Variables

**Required in `.env` file:**
```bash
# OpenAI Configuration
OPENAI_API_KEY=your_key_here
MODEL_NAME=c1/openai/gpt-5/v-20250930
MODEL_BASE_URL=https://api.thesys.dev/v1/embed/

# Database (configured in docker-compose.yml)
DATABASE_URL=postgresql://stockanalysis:devpassword@postgres:5432/stockanalysis
REDIS_URL=redis://redis:6379/0
```

## Database Migrations

### View Current Migration
```bash
docker compose exec backend alembic current
```

### Apply Migrations
```bash
docker compose exec backend alembic upgrade head
```

### Create New Migration
```bash
# Auto-generate from model changes
docker compose exec backend alembic revision --autogenerate -m "description"

# Manual migration
docker compose exec backend alembic revision -m "description"
```

### Migration History
```bash
docker compose exec backend alembic history
```

## Database Access

### Connect to PostgreSQL
```bash
docker compose exec postgres psql -U stockanalysis -d stockanalysis
```

### Useful SQL Commands
```sql
-- List all tables
\dt

-- Describe table
\d table_name

-- Check pgvector extension
SELECT * FROM pg_extension WHERE extname = 'vector';

-- View conversation embeddings
SELECT id, thread_id, user_id, created_at
FROM conversation_embeddings
LIMIT 10;

-- Exit
\q
```

### Connect to Redis
```bash
docker compose exec redis redis-cli

# View all keys
KEYS *

# Get cache value
GET "cache:some_key"

# Clear all cache
FLUSHALL

# Exit
exit
```

## Architecture Overview

### Tech Stack
```
Frontend: React + TypeScript + Vite
Backend: FastAPI + LangGraph + Python 3.10
Database: PostgreSQL 16 + pgvector
Cache: Redis 7
Vector Search: pgvector (IVFFlat indexes)
Embeddings: OpenAI text-embedding-3-small (1536 dimensions)
LLM: GPT-4 via LangGraph
```

### Key Components

**Backend Structure:**
```
backend/
├── app/
│   ├── core/
│   │   ├── cache.py          # Redis + LangCache setup
│   │   ├── correlation.py    # Request correlation IDs
│   │   ├── database.py       # Database connection
│   │   └── logging.py        # Structured logging
│   ├── models/
│   │   ├── chat.py           # Pydantic models (API)
│   │   └── database.py       # SQLAlchemy models (DB)
│   ├── routers/
│   │   └── chat.py           # Chat endpoints
│   ├── services/
│   │   └── agent.py          # LangGraph agent
│   ├── tools/
│   │   ├── stock_price.py    # 60s cache + timestamps
│   │   ├── balance_sheet.py  # 24h cache
│   │   ├── historical_price.py # 1h cache
│   │   └── company_logo.py   # 7d cache
│   └── main.py               # FastAPI app
├── alembic/                  # Database migrations
├── tests/                    # Unit + integration tests
└── pyproject.toml            # Dependencies
```

**Database Schema:**
```sql
users
├── id
├── email (unique)
├── hashed_password
├── country
└── preferred_currency

conversations
├── id
├── user_id → users.id
├── thread_id (unique)
└── title

messages
├── id
├── conversation_id → conversations.id
├── role (user/assistant/system)
├── content
└── timestamp

conversation_embeddings  ← Story 2.1
├── id
├── thread_id
├── user_id → users.id
├── content (text)
├── embedding (vector 1536)  ← pgvector
├── meta (jsonb)
└── created_at

Indexes:
- IVFFlat on embedding (lists=100) for similarity search
```

## Caching Strategy (Story 1.7)

| Data Type | TTL | Reason |
|-----------|-----|--------|
| Stock prices | 60s | Balance freshness vs API calls |
| Balance sheets | 24h | Updated quarterly |
| Historical data | 1h | Doesn't change |
| Company logos | 7d | Rarely change |

Cached data includes `cached_at` timestamp shown to users for transparency.

## Important Naming Conventions

### metadata → meta
**Why**: SQLAlchemy reserves `metadata` for internal use.

**Correct usage:**
```python
# Database column
meta = Column(JSONB)

# Accessing data
result.meta.get("user_message")

# Creating records
ConversationEmbedding(
    thread_id="abc",
    content="...",
    embedding=...,
    meta={"tokens": 10, "tickers": ["AAPL"]}
)
```

**Incorrect (will error):**
```python
metadata = Column(JSONB)  # ❌ SQLAlchemy reserved word
```

## Testing

### Run All Tests
```bash
cd backend
pytest
```

### Run Specific Tests
```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Specific file
pytest tests/unit/models/test_database.py

# Specific test
pytest tests/unit/models/test_database.py::TestUserModel::test_create_user
```

### Coverage Report
```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## Troubleshooting

### Backend won't start
```bash
# Check logs
docker compose logs backend

# Rebuild
docker compose build backend

# Fresh start
docker compose down -v && docker compose up -d
```

### Database connection error
```bash
# Check PostgreSQL is running
docker compose ps postgres

# Check health
docker compose exec postgres pg_isready -U stockanalysis

# Restart
docker compose restart postgres
```

### Redis connection error
```bash
# Check Redis is running
docker compose ps redis

# Test connection
docker compose exec redis redis-cli ping

# Should return: PONG
```

### Alembic migration errors
```bash
# Check current state
docker compose exec backend alembic current

# Show history
docker compose exec backend alembic history

# Downgrade one version
docker compose exec backend alembic downgrade -1

# Upgrade to head
docker compose exec backend alembic upgrade head
```

### pgvector not working
```bash
# Verify extension installed
docker compose exec postgres psql -U stockanalysis -d stockanalysis \
  -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

# Should show: vector | 0.8.1

# If not, check image
docker compose exec postgres psql -U stockanalysis -d stockanalysis \
  -c "SELECT version();"

# Should include: PostgreSQL 16.x
```

## Development Workflow

### 1. Make Code Changes
Edit files in `backend/app/` or `frontend/src/`

### 2. Changes Auto-Reload
Both backend and frontend have hot reload enabled:
- Backend: Uvicorn `--reload` mode
- Frontend: Vite development server (polls for changes, because file-change events don't fire on the Windows `/mnt/c` filesystem)

**Option A - everything in Docker:**
```bash
docker compose up        # frontend at http://localhost:3000
```

**Option B - frontend on your own terminal, rest in Docker:**
```bash
docker compose up -d postgres redis backend   # or: docker compose stop frontend
cd frontend
npm install --legacy-peer-deps                # first time / after package changes
npm run dev                                   # http://localhost:3000, proxies /api to localhost:8888
```
Run `npm run dev` from `frontend/`, and stop the Docker frontend first (it also uses port 3000).
The first page load after a dependency change can take a minute while Vite pre-bundles dependencies.

### 3. Add Database Changes
```bash
# 1. Edit model in app/models/database.py
# 2. Generate migration
docker compose exec backend alembic revision --autogenerate -m "add new field"

# 3. Review migration in alembic/versions/
# 4. Apply migration
docker compose exec backend alembic upgrade head
```

### 4. Run Tests
```bash
docker compose exec backend pytest
```

### 5. Commit Changes
```bash
git add .
git commit -m "descriptive message"
```

## Next Steps (Story 2.2)

To continue implementing Epic 2, see:
- **Full details**: `EPIC.md` Story 2.2
- **Summary**: `STORY_2.1_COMPLETION_SUMMARY.md`

Quick overview of Story 2.2:
1. Create embedding service using OpenAI text-embedding-3-small
2. Set up LangCache for semantic caching (60-90% cost savings)
3. Integrate with LangGraph agent
4. Test embedding generation and caching

## Useful Resources

- **Project Vision**: `PRODUCT_VISION.md`
- **System Architecture**: `SYSTEM_ARCHITECTURE.md`
- **Epic Details**: `EPIC.md`
- **Story 2.1 Summary**: `STORY_2.1_COMPLETION_SUMMARY.md`
- **Docker Setup**: `DOCKER_SETUP.md`
- **Vector DB Comparison**: `VECTOR_DATABASE_COMPARISON.md`
