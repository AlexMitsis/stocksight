# Stock Analysis Platform - Status

---

## Current State

### Completed Work ✅

**Epic 1: Core Backend Infrastructure** (8 stories) - COMPLETE
- FastAPI backend with LangChain agent
- Stock analysis tools (price, historical data, balance sheet, news, logos)
- PostgreSQL + Docker setup
- Redis caching layer
- Structured logging with correlation IDs

**Epic 2: RAG with pgvector** (7 stories) - COMPLETE
- pgvector setup and integration
- OpenAI Embedding Service
- Context storage and retrieval services
- RAG integration into chat endpoint
- Performance monitoring and quality tuning

**Epic 3: European Market Foundation** (5 stories) - COMPLETE
- ✅ Story 3.1: Multi-Currency Support (EUR, GBP, CHF, USD)
  - Real-time currency conversion via exchangerate-api.com
  - User preferred currency in profile
  - All stock/financial tools currency-aware
- ✅ Story 3.3: User Authentication System
  - JWT authentication (access + refresh tokens)
  - User registration and login
  - Password hashing with bcrypt
  - Protected endpoints
- ✅ Story 3.4: Frontend Authentication & OAuth Integration
  - Login & signup pages with shadcn/ui
  - OAuth infrastructure (Google/GitHub) - requires credentials to test
  - Protected routes and auth context
  - Password reset, profile management
- ✅ Story 3.6: Remove LangCache (5 points) - Completed January 26, 2026
  - Removed semantic LLM caching (445 lines removed)
  - Preserved tool-level caching (stock prices, balance sheets, logos)
  - Ensures real-time accuracy for stock data

**Epic 4: Portfolio Management** (4 stories complete)
- ✅ Story 4.1: Manual Portfolio Entry with CSV Import (8 points)
  - Holdings CRUD operations (Create, Read, Update, Delete)
  - CSV import with validation and duplicate detection
  - Sortable holdings table
  - Portfolio summary cards (total value, cost, gains)
  - Multi-currency integration
- ✅ Story 4.2: Portfolio Performance Dashboard (15 points)
  - Real-time portfolio performance tracking
  - Portfolio Value Over Time chart
  - Portfolio Allocation pie chart
  - Gains/Losses bar chart with purchase price comparison
  - Top performers display
  - Multi-currency performance tracking
- ✅ Story 4.4: Auto-Fill Purchase Price with VWAP (5 points)
  - VWAP endpoint for historical price lookup
  - Auto-fill purchase price when date selected
  - Weekend/holiday handling
  - Debounced API calls
  - Manual override support
- ✅ Story 4.5: Bug Fixes & Transaction History (13 points)
  - Atomic transaction/holdings sync (holdings are only written via transactions)
  - Historical exchange rates, TransactionHistory + AddTransactionForm
  - FIX-007 (SELL rejection → 400) and FIX-008 (SELL delete cost basis) fixed
  - ⏸️ FIFO realized gains (Step 10) deferred - tracked as FIX-003

**Epic 5: Production Readiness & Polish** (1 story complete)
- ✅ Story 5.1: Frontend Polish & UX
  - Shared `AppLayout` layout route (nav, theme toggle, logout) for all pages except Chat
  - Mobile slide-out nav (vaul), page transitions
  - Count-up metrics, card hover / button press micro-interactions
  - Loading skeletons, empty states, Sonner toasts
- 📝 Story 5.2: TradingView Chart via MCP - Draft
- 📝 Deployment & observability - Planned (`docs/OBSERVABILITY_AND_DEPLOYMENT_PLAN.md`)

**Recent Fixes**
- CSV import was broken: `transactions.type` was VARCHAR(10), too short for `TRANSFER_IN`/`TRANSFER_OUT` → migration 011 widens it to VARCHAR(20)
- Removed obsolete startup holdings migration (crashed on every boot) and unused `PortfolioService` write methods
- Reset `admin@test.com` portfolio (dev test data out of sync) and re-imported `sample_portfolio.csv`
- Open items tracked in `PENDING_FIXES.md` (FIX-003, 009, 010, 011)

### What's Running

The application is fully functional with:
- ✅ AI-powered stock analysis chat
- ✅ Real-time streaming responses
- ✅ RAG-enhanced conversations with context memory
- ✅ User authentication and authorization
- ✅ Multi-currency support (EUR, GBP, CHF, USD)
- ✅ Portfolio management with CSV import
- ✅ Portfolio performance dashboard with charts
- ✅ VWAP auto-fill for purchase prices
- ✅ Modern React frontend with GenUI SDK
- ✅ Docker-based development environment

### Quick Start

1. **Start services:**
   ```bash
   docker-compose up -d
   ```

2. **Create test account:**
   ```bash
   docker-compose exec backend python create_admin.py
   ```
   - Email: `admin@test.com`
   - Password: `Admin123!`

3. **Access application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8888
   - API Docs: http://localhost:8888/docs

---

## Architecture Overview

### Technology Stack

**Backend:**
- FastAPI 0.124.4
- LangChain `create_agent` with `c1/openai/gpt-5` via TheSys C1 API
- PostgreSQL 16 with pgvector 0.8.1
- Redis Stack Server (with RediSearch)
- SQLAlchemy 2.0 + Alembic
- OpenAI text-embedding-3-small (1536 dimensions)

**Frontend:**
- React 19 with TypeScript
- GenUI SDK (@thesysai/genui-sdk)
- Vite build tool
- shadcn/ui components + Tailwind CSS
- Axios with JWT interceptors

**Infrastructure:**
- Docker Compose (4 services)
- Hot reload for development (backend only for now - see FIX-011)
- Structured logging
- Prometheus metrics at /metrics

### Database Schema

**users** - User accounts with authentication
- JWT tokens, bcrypt password hashing
- Country and preferred currency settings

**conversations** - Chat thread tracking
- Links to users and messages
- Thread IDs for isolation

**messages** - Chat history
- User and assistant messages
- Token usage tracking

**conversation_embeddings** - RAG vector storage
- 1536-dimensional embeddings via pgvector
- IVFFlat index for similarity search
- Metadata (tickers, timestamps)

**password_reset_tokens** - Password reset flow
- SHA-256 hashed tokens
- Single-use, 1-hour expiration

### Key Features

**Tool-Level Caching:**
- Stock prices: 60 second cache
- Historical prices: 1 hour cache
- Balance sheets: 24 hour cache
- Company logos: 7 day cache
- Stock news: No cache (always fresh)

**RAG (Retrieval-Augmented Generation):**
- Context-aware responses using past conversations
- Top-k retrieval with cosine similarity
- User-isolated context (thread_id + user_id)

**Authentication:**
- JWT access tokens (30 min)
- JWT refresh tokens (7 days)
- OAuth ready (Google/GitHub)
- Password reset flow

---

## Next Steps

### Option 1: Local Dev Experience (FIX-011) - Quick
- Frontend hot reload in Docker (`server.watch.usePolling`) and documented host `npm run dev` workflow

### Option 2: Deployment & Observability (Epic 5)
- Azure Bicep IaC, GitHub Actions CD, Prometheus + Grafana
- Plan: `docs/OBSERVABILITY_AND_DEPLOYMENT_PLAN.md`

### Option 3: Test Suite Health (FIX-010)
- 26 failing / 40 erroring backend tests predate October 2026 work; clean up before relying on CI

### Option 4: Story 3.7 - Local Data Lake (21 points)
- PostgreSQL data lake with S&P 500 stocks, DB-first agent

### Option 5: Story 5.2 - TradingView Charts in Chat (8 points)

### Optional Enhancements

**Security:**
- Move JWT tokens from localStorage to httpOnly cookies
- Add CSRF protection
- Implement rate limiting
- Email verification for new accounts
- Two-factor authentication (2FA)

**Chat Features:**
- Multiple conversation threads
- Conversation search
- Export transcripts
- Conversation sharing

---

## Testing & Verification

### Test Account

Default admin account for testing:
- Email: `admin@test.com`
- Password: `Admin123!`

See `ADMIN_ACCOUNT_SETUP.md` for details.

### Verification Commands

**Check services:**
```bash
docker-compose ps
```

**View logs:**
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
```

**Check database migration:**
```bash
docker-compose exec backend alembic current
# Expected: 011_widen_transaction_type (head)
```

**Run tests:**
```bash
docker-compose exec backend pytest
```

**Access database:**
```bash
docker-compose exec postgres psql -U stockanalysis -d stockanalysis
```

**Check Redis:**
```bash
docker-compose exec redis redis-cli ping
```

### API Testing

**Register user:**
```bash
curl -X POST http://localhost:8888/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"SecurePass123"}'
```

**Login:**
```bash
curl -X POST http://localhost:8888/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"SecurePass123"}'
```

**Chat (authenticated):**
```bash
curl -X POST http://localhost:8888/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{
    "prompt": {"content": "What is AAPL stock price?", "id": "1", "role": "user"},
    "threadId": "test-123",
    "responseId": "resp-1"
  }'
```

---

## Documentation Index

### Essential Documentation
- **CLAUDE.md** - Developer guide for Claude Code (critical patterns and rules)
- **EPIC.md** - Master specification index (links to all epic files)
  - **EPIC_1.md** - Core Infrastructure & Testing (COMPLETE)
  - **EPIC_2.md** - Token Management & RAG Implementation (COMPLETE)
  - **EPIC_3.md** - European Market Foundation (COMPLETE)
  - **EPIC_4.md** - Portfolio Management (COMPLETE except FIFO gains)
  - **EPIC_5.md** - Production Readiness & Polish (IN PROGRESS)
- **FUTURE_IMPROVEMENTS.md** - Deprioritized features (ETF tools, tax system)
- **SYSTEM_ARCHITECTURE.md** - System design and data flows
- **PRODUCT_VISION.md** - Product strategy and roadmap
- **STATUS.md** - This file (current status)

### Setup & Configuration
- **README.md** - Project overview
- **DOCKER_SETUP.md** - Docker configuration details
- **QUICK_START_GUIDE.md** - Development commands and troubleshooting
- **ADMIN_ACCOUNT_SETUP.md** - Test account creation

### Authentication
- **AUTHENTICATION_PLAN.md** - Auth system design (Story 3.3)
- **AUTH_ENHANCEMENTS_SUMMARY.md** - Completed auth features
- **OAUTH_SETUP_GUIDE.md** - Google/GitHub OAuth configuration

### Technical Guides
- **RAG_QUALITY_GUIDE.md** - RAG testing and tuning best practices
- **VECTOR_DATABASE_COMPARISON.md** - Why pgvector over Pinecone
- **CHAT_STREAMING_FIX_SUMMARY_2025-12-29.md** - Critical LangChain agent fix
- **CI_CD_DOCUMENTATION.md** - GitHub Actions setup

### Future Planning
- **STORY_3.7_LOCAL_DATA_LAKE.md** - Future story plan
- **STORY_5.2_TRADINGVIEW_CHART_MCP.md** - TradingView MCP integration (draft)
- **OBSERVABILITY_AND_DEPLOYMENT_PLAN.md** - Azure deployment + monitoring plan
- **PENDING_FIXES.md** - Open bugs and tech debt

### Archived Documentation
See `docs/archive/completed-stories/` for:
- Epic 2 story completion summaries (2.1-2.7)
- Story 3.3 and 3.4 completion summaries
- Testing results and implementation details

---

## Cost Savings Summary

### pgvector vs Pinecone
- **Pinecone Starter:** $70/month ($840/year)
- **pgvector (self-hosted):** $0 (uses existing PostgreSQL)
- **Savings:** $840/year

### LangCache (REMOVED - January 2026)
- LangCache semantic caching was removed in Story 3.6
- **Reason:** Stock data requires real-time accuracy; caching LLM responses caused stale market data
- **Trade-off:** ~$3,000/year additional LLM costs for 100% accurate data
- Tool-level caching preserved (balance sheets, logos, etc.)

### text-embedding-3-small
- **Cost:** $0.00002 per 1K tokens
- **vs ada-002:** 62% cheaper
- **Estimated savings:** $500-1000/year

**Total Annual Savings:** ~$1,300-1,800 (after LangCache removal)

---

## Key Decisions & Conventions

### Critical Rules (from CLAUDE.md)
1. **Never change LangChain agent pattern** - Use `langchain.agents.create_agent`, NOT `langgraph.prebuilt`
2. **Stream plain text** - GenUI SDK expects plain text, not SSE format
3. **Don't modify ChatPage.tsx extensively** - Use GenUI SDK as-is with minimal customization
4. **Use `langchain.agents.create_agent`** - See CHAT_STREAMING_FIX for details

### Naming Conventions
- **metadata → meta** - SQLAlchemy reserves `metadata` as internal attribute

### Caching Strategy
| Data | TTL | Timestamp |
|------|-----|-----------|
| Stock prices | 60s | Yes |
| Historical prices | 1h | Yes |
| Balance sheets | 24h | Yes |
| Company logos | 7d | No |

### Vector Index Configuration
- **Algorithm:** IVFFlat (approximate nearest neighbor)
- **Lists:** 100 (optimal for 1K-100K vectors)
- **Distance metric:** Cosine distance
- **Rebuild trigger:** When dataset grows 10x

---

## Production Readiness

### Ready ✅
- Authentication system (JWT + bcrypt)
- Password reset flow
- RAG system with pgvector
- Redis caching
- Structured logging
- Error handling
- CORS configuration
- Database migrations
- Docker containers

### Needs Production Setup ⚠️
- Email service (replace mock with SendGrid/AWS SES)
- OAuth credentials (Google/GitHub)
- Rate limiting (optional but recommended)
- SSL/TLS certificates
- Domain setup
- Monitoring/alerting (Sentry, Datadog)
- Database backup strategy
- CI/CD pipeline (deployment stage - see OBSERVABILITY_AND_DEPLOYMENT_PLAN.md)

---

**Epics 1-4 complete, Story 5.1 complete. Next: local dev fixes (FIX-011), then deployment.**

For detailed implementation plans and specifications, see EPIC.md (index) and individual epic files (EPIC_1.md through EPIC_5.md). Deprioritized features are documented in FUTURE_IMPROVEMENTS.md.
