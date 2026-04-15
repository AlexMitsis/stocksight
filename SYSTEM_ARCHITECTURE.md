# Stock Analysis Platform - System Architecture

**Complete System Design** (After all Epics)

---

## High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                         ┌────────────┴────────────┐
                         │                         │
                    ┌────▼────┐              ┌────▼────┐
                    │ Browser │              │ Mobile  │
                    │  (Web)  │              │   App   │
                    └────┬────┘              └────┬────┘
                         │                         │
                         └────────────┬────────────┘
                                      │
                         ┌────────────▼─────────────┐
                         │   React Frontend (Vite)  │
                         │   - Chat Interface       │
                         │   - Portfolio Dashboard  │
                         │   - Stock Watchlists     │
                         └────────────┬─────────────┘
                                      │
                                   HTTPS
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY / LOAD BALANCER                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                         ┌────────────┴────────────┐
                         │                         │
┌────────────────────────▼─────────────────────────▼──────────────────────────┐
│                          APPLICATION LAYER                                   │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  FastAPI Backend                                                      │  │
│  │  ┌─────────────────┐  ┌──────────────┐  ┌──────────────────────┐   │  │
│  │  │ Chat Router     │  │ Auth Router  │  │ Portfolio Router     │   │  │
│  │  │ /api/chat       │  │ /api/auth/*  │  │ /api/portfolio/*     │   │  │
│  │  └────────┬────────┘  └──────┬───────┘  └──────────┬───────────┘   │  │
│  │           │                   │                      │                │  │
│  │  ┌────────▼───────────────────▼──────────────────────▼────────────┐ │  │
│  │  │                    Middleware Layer                            │ │  │
│  │  │  - Logging (Correlation IDs)                                   │ │  │
│  │  │  - Authentication (JWT)                                        │ │  │
│  │  │  - CORS                                                        │ │  │
│  │  │  - Rate Limiting                                               │ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  │           │                                                          │  │
│  │  ┌────────▼──────────────────────────────────────────────────────┐ │  │
│  │  │                    Service Layer                              │ │  │
│  │  │  ┌───────────────┐  ┌──────────────┐  ┌──────────────────┐  │ │  │
│  │  │  │ Agent Service │  │ Embedding    │  │ Context Storage  │  │ │  │
│  │  │  │ (LangChain)   │  │ Service      │  │ & Retrieval      │  │ │  │
│  │  │  │ - Stock Agent │  │ (OpenAI)     │  │ (RAG)            │  │ │  │
│  │  │  │ - Tools       │  │ - LangCache  │  │ - pgvector       │  │ │  │
│  │  │  └───────┬───────┘  └──────┬───────┘  └─────────┬────────┘  │ │  │
│  │  │          │                  │                     │            │ │  │
│  │  │  ┌───────▼──────────────────▼─────────────────────▼─────────┐│ │  │
│  │  │  │              Tools Layer                                  ││ │  │
│  │  │  │  - get_stock_price()    - get_balance_sheet()            ││ │  │
│  │  │  │  - get_historical_price() - get_stock_news()             ││ │  │
│  │  │  │  - calculate_portfolio() - tax_optimization()            ││ │  │
│  │  │  └───────────────────────────────────────────────────────────┘│ │  │
│  │  └────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                         ┌────────────┴────────────┐
                         │                         │
┌────────────────────────▼─────────────────────────▼────────────────────┐
│                           DATA LAYER                                   │
│                                                                        │
│  ┌──────────────────┐  ┌──────────────────┐                          │
│  │  PostgreSQL      │  │  Redis           │                          │
│  │                  │  │                  │                          │
│  │  Tables:         │  │  Caches:         │                          │
│  │  - users         │  │  - Stock prices  │                          │
│  │  - conversations │  │  - Balance sheets│                          │
│  │  - messages      │  │  - Historical    │                          │
│  │  - portfolios    │  │  - LangCache     │                          │
│  │  - holdings      │  │    (embeddings)  │                          │
│  │  - embeddings    │  │  - LangCache     │                          │
│  │    (pgvector)    │  │    (LLM)         │                          │
│  │  - tax_rules     │  │                  │                          │
│  │  - legal_docs    │  │                  │                          │
│  │                  │  │                  │                          │
│  │  Extensions:     │  │                  │                          │
│  │  - pgvector      │  │                  │                          │
│  └──────────────────┘  └──────────────────┘                          │
└────────────────────────────────────────────────────────────────────────┘
                                      │
                         ┌────────────┴────────────┐
                         │                         │
┌────────────────────────▼─────────────────────────▼──────────────────────────┐
│                       EXTERNAL SERVICES LAYER                                │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │  OpenAI          │  │  yfinance        │  │  Currency APIs           │ │
│  │                  │  │  (Yahoo Finance) │  │  (Exchange Rates)        │ │
│  │  - GPT-4/5       │  │                  │  │                          │ │
│  │  - Embeddings    │  │  - Stock prices  │  │  - EUR/USD/GBP/CHF       │ │
│  │  - Text gen      │  │  - Balance sheet │  │  - Real-time rates       │ │
│  │                  │  │  - Historical    │  │                          │ │
│  │                  │  │  - News          │  │                          │ │
│  │                  │  │  - Company info  │  │                          │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘ │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐ │
│  │  European Stock  │  │  Tax Services    │  │  Legal DBs               │ │
│  │  Exchanges       │  │  (Country APIs)  │  │  (Deprioritized)         │ │
│  │                  │  │                  │  │                          │ │
│  │  - Euronext      │  │  - DE tax calc   │  │  - MiFID II rules        │ │
│  │  - LSE           │  │  - FR tax calc   │  │  - PRIIPS docs           │ │
│  │  - Xetra         │  │  - UK tax calc   │  │  - Country regulations   │ │
│  │  - SIX Swiss     │  │  - CH tax calc   │  │  (FUTURE_IMPROVEMENTS)   │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagrams

### 1. User Chat Request Flow (Epic 2 - RAG)

```
┌──────┐                                                                ┌──────────┐
│ User │                                                                │ Frontend │
└───┬──┘                                                                └────┬─────┘
    │                                                                        │
    │ 1. "What's AAPL price?"                                               │
    │────────────────────────────────────────────────────────────────────>  │
    │                                                                        │
    │                                                              ┌─────────▼─────────┐
    │                                                              │  FastAPI Backend  │
    │                                                              └─────────┬─────────┘
    │                                                                        │
    │                                              2. Generate correlation ID│
    │                                                      Log request start │
    │                                                                        │
    │                                               ┌──────────────────────▼──────────┐
    │                                               │   Context Retrieval Service      │
    │                                               │   3. Embed query (with LangCache)│
    │                                               │   4. Search pgvector for similar │
    │                                               │      past conversations          │
    │                                               └──────────────────────┬──────────┘
    │                                                                      │
    │                                                    5. Return top 5 relevant
    │                                                       conversation contexts
    │                                                                      │
    │                                               ┌──────────────────────▼──────────┐
    │                                               │      LangChain Agent            │
    │                                               │   6. Combine query + context    │
    │                                               │   7. Check LangCache (LLM)      │
    │                                               │   8. Call LLM if cache miss     │
    │                                               │   9. Call tools as needed       │
    │                                               └──────────────────────┬──────────┘
    │                                                                      │
    │                                                          ┌───────────▼──────────┐
    │                                                          │   Tool: Stock Price  │
    │                                                          │   10. Check Redis    │
    │                                                          │   11. Call yfinance  │
    │                                                          │       if cache miss  │
    │                                                          └───────────┬──────────┘
    │                                                                      │
    │                                                          12. Return price data
    │                                                                      │
    │                                               ┌──────────────────────▼──────────┐
    │                                               │   LangChain Agent               │
    │                                               │   13. Generate response         │
    │                                               │   14. Stream to user            │
    │                                               └──────────────────────┬──────────┘
    │                                                                      │
    │                                               ┌──────────────────────▼──────────┐
    │                                               │   Context Storage Service       │
    │                                               │   15. Embed conversation turn   │
    │                                               │   16. Store in pgvector         │
    │                                               │   17. Log completion time       │
    │                                               └─────────────────────────────────┘
    │                                                                      │
    │  18. Stream response: "AAPL is trading at $175.43 (as of ...)"      │
    │<─────────────────────────────────────────────────────────────────────│
    │
```

**Key Points:**

- Correlation ID tracks entire request
- RAG retrieves relevant past context
- LangCache reduces API calls
- Redis caches external data
- pgvector stores conversation embeddings

---

### 2. New User Registration Flow (Epic 3)

```
┌──────┐                                                                ┌──────────┐
│ User │                                                                │ Frontend │
└───┬──┘                                                                └────┬─────┘
    │                                                                        │
    │ 1. Register (email, password, country, currency)                      │
    │────────────────────────────────────────────────────────────────────>  │
    │                                                                        │
    │                                                              ┌─────────▼─────────┐
    │                                                              │ Auth Router       │
    │                                                              │ /api/auth/register│
    │                                                              └─────────┬─────────┘
    │                                                                        │
    │                                                       2. Validate input
    │                                                       3. Hash password
    │                                                                        │
    │                                               ┌──────────────────────▼──────────┐
    │                                               │    PostgreSQL (users table)     │
    │                                               │    4. Insert new user           │
    │                                               │    5. Return user_id            │
    │                                               └──────────────────────┬──────────┘
    │                                                                      │
    │                                               ┌──────────────────────▼──────────┐
    │                                               │     Auth Service                │
    │                                               │     6. Generate JWT token       │
    │                                               │     7. Include user_id + email  │
    │                                               └──────────────────────┬──────────┘
    │                                                                      │
    │  8. Return JWT token + user profile                                 │
    │<─────────────────────────────────────────────────────────────────────│
    │
    │ 9. Store token in localStorage/cookies
    │ 10. Include in Authorization header for future requests
```

---

### 3. Portfolio Analysis Flow (Epic 4)

```
┌──────┐                                                                ┌──────────┐
│ User │                                                                │ Frontend │
└───┬──┘                                                                └────┬─────┘
    │                                                                        │
    │ 1. "Analyze my portfolio"                                             │
    │────────────────────────────────────────────────────────────────────>  │
    │                                                                        │
    │                                                              ┌─────────▼─────────┐
    │                                                              │ Portfolio Router  │
    │                                                              │ /api/portfolio    │
    │                                                              └─────────┬─────────┘
    │                                                                        │
    │                                                       2. Verify JWT token
    │                                                       3. Get user_id
    │                                                                        │
    │                                               ┌──────────────────────▼──────────┐
    │                                               │   PostgreSQL                    │
    │                                               │   4. Fetch user holdings        │
    │                                               │   SELECT * FROM holdings        │
    │                                               │   WHERE user_id = X             │
    │                                               └──────────────────────┬──────────┘
    │                                                                      │
    │                                               5. Holdings: [AAPL: 10, MSFT: 5]
    │                                                                      │
    │                                               ┌──────────────────────▼──────────┐
    │                                               │   Tools: get_stock_price (x2)   │
    │                                               │   6. Get prices for AAPL, MSFT  │
    │                                               │   7. Check Redis cache first    │
    │                                               └──────────────────────┬──────────┘
    │                                                                      │
    │                                               8. Current values calculated
    │                                                                      │
    │                                               ┌──────────────────────▼──────────┐
    │                                               │   Currency Service              │
    │                                               │   9. Convert to EUR             │
    │                                               │   10. Check Redis cache         │
    │                                               └──────────────────────┬──────────┘
    │                                                                      │
    │                                               ┌──────────────────────▼──────────┐
    │                                               │   LangChain Agent               │
    │                                               │   14. Generate analysis         │
    │                                               │   15. Include RAG context       │
    │                                               │   16. Tax implications (future) │
    │                                               └──────────────────────┬──────────┘
    │                                                                      │
    │  17. Portfolio analysis with recommendations                         │
    │<─────────────────────────────────────────────────────────────────────│
```

---

## Technology Stack Summary

### Frontend

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite 7
- **UI Library**: Material-UI (MUI)
- **State Management**: Context API / Redux (if needed)
- **Testing**: Vitest + React Testing Library

### Backend

- **Framework**: FastAPI (Python 3.10+)
- **AI/ML**: LangChain + OpenAI
- **Package Manager**: uv
- **Testing**: pytest + pytest-asyncio
- **Linting**: black + flake8 + mypy

### Databases

- **Relational**: PostgreSQL 15 + SQLAlchemy + Alembic
- **Cache**: Redis 7 + LangCache
- **Vector**: pgvector extension

### Infrastructure

- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana (Epic 8)
- **Logging**: Loguru + structured JSON

### External Services

- **LLM**: OpenAI GPT-4/5
- **Embeddings**: OpenAI text-embedding-3-small
- **Market Data**: yfinance (Yahoo Finance)
- **Currency**: exchangerate-api.io

---

## Deployment Architecture (Epic 8)

```
                      ┌─────────────────────────────┐
                      │   CloudFlare / CDN          │
                      │   - DDoS protection         │
                      │   - Static asset caching    │
                      └──────────────┬──────────────┘
                                     │
                      ┌──────────────▼──────────────┐
                      │   Load Balancer (Nginx)     │
                      │   - SSL termination         │
                      │   - Rate limiting           │
                      └──────────────┬──────────────┘
                                     │
                ┌────────────────────┼────────────────────┐
                │                    │                    │
     ┌──────────▼──────────┐ ┌──────▼─────────┐ ┌──────▼─────────┐
     │ Frontend Container  │ │ Backend Pod 1  │ │ Backend Pod 2  │
     │ (Static files)      │ │ (FastAPI)      │ │ (FastAPI)      │
     └─────────────────────┘ └────────┬───────┘ └────────┬───────┘
                                      │                   │
                      ┌───────────────┴───────────────────┘
                      │
         ┌────────────┴────────────┬──────────────┬──────────────┐
         │                         │              │
┌────────▼─────────┐  ┌───────────▼──────┐ ┌─────▼──────┐
│ PostgreSQL       │  │ Redis Cluster    │ │ Prometheus │
│ (Managed)        │  │ (Managed)        │ │ Grafana    │
│ - AWS RDS        │  │ - AWS ElastiCache│ │            │
│ - Backups        │  │ - 3 nodes        │ │            │
└──────────────────┘  └──────────────────┘ └────────────┘
```

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Security Layers                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. Network Layer                                                        │
│     - HTTPS only (TLS 1.3)                                              │
│     - Firewall rules (only ports 80, 443 open)                         │
│     - DDoS protection (CloudFlare)                                      │
│                                                                          │
│  2. Application Layer                                                    │
│     - JWT authentication                                                 │
│     - CORS restrictions                                                  │
│     - Rate limiting (100 req/min per IP)                                │
│     - Input validation (Pydantic models)                                │
│     - SQL injection prevention (SQLAlchemy ORM)                         │
│     - XSS protection (Content-Security-Policy headers)                  │
│                                                                          │
│  3. Data Layer                                                           │
│     - Password hashing (bcrypt)                                         │
│     - Encrypted at rest (database encryption)                           │
│     - Encrypted in transit (TLS)                                        │
│     - API keys in environment variables (never committed)               │
│     - Secrets management (AWS Secrets Manager / Vault)                  │
│                                                                          │
│  4. Monitoring Layer                                                     │
│     - Request logging (correlation IDs)                                 │
│     - Anomaly detection (unusual request patterns)                      │
│     - Alerts (failed login attempts, unusual queries)                   │
│     - Audit logs (user actions tracked)                                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Scaling Strategy

### Phase 1: MVP (Current)

- **Users**: <1,000
- **Infrastructure**: Single server Docker Compose
- **Database**: PostgreSQL single instance
- **Cost**: ~$50/month

### Phase 2: Growth (10k users)

- **Users**: 1,000 - 10,000
- **Infrastructure**: Multiple backend pods
- **Database**: Managed PostgreSQL (AWS RDS)
- **Cache**: Redis cluster
- **Cost**: ~$500/month

### Phase 3: Scale (100k+ users)

- **Users**: 10,000+
- **Infrastructure**: Auto-scaling Kubernetes cluster
- **Database**: PostgreSQL read replicas
- **Vector DB**: Consider migrating to Pinecone
- **CDN**: CloudFlare for global distribution
- **Cost**: $2,000+/month

---

## Performance Targets

| Metric | Target | Current (MVP) |
|--------|--------|---------------|
| API Response Time | <200ms (p95) | ~500ms |
| Chat Response Time | <2s (first token) | ~2s |
| RAG Context Retrieval | <100ms | TBD (Epic 2) |
| Cache Hit Rate | >80% | ~75% |
| Database Query Time | <50ms | <20ms |
| Concurrent Users | 1000+ | ~10 |
| Uptime | 99.9% | TBD (Epic 8) |

---

This is the complete system architecture after all epics are implemented!
