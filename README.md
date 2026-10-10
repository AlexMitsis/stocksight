# Stock Analysis - AI-Powered Financial Analysis Platform

A full-stack web application that provides intelligent stock market analysis through an AI-powered chat interface, portfolio management, and multi-currency support. Built with FastAPI, LangChain, React, and TypeScript.

## Overview

Stock Analysis combines Large Language Models (LLMs) with real-time market data to deliver professional-grade financial insights. Features include an AI chat assistant, portfolio tracking with performance analytics, and RAG-enhanced conversation memory.

### Key Features

- **AI Stock Analyst** - Chat with an expert financial analyst powered by GPT-5
- **Portfolio Management** - Track holdings, import via CSV, view performance dashboards
- **Multi-Currency Support** - EUR, GBP, CHF, USD with historical exchange rate conversion
- **RAG Memory** - Context-aware responses using conversation history (pgvector)
- **Real-Time Data** - Live stock prices, historical OHLCV, financials, news via yfinance

## Quick Start with Docker

The fastest way to run the entire application locally:

```bash
# 1. Copy environment variables
cp .env.example .env

# 2. Add your OpenAI API key to .env
# Edit .env and set: OPENAI_API_KEY=your-key-here

# 3. Start everything!
docker-compose up
```

That's it! The application will be available at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8888
- **API Docs**: http://localhost:8888/docs

Docker Compose automatically:
- ✅ Starts PostgreSQL 16 with pgvector
- ✅ Starts Redis with RediSearch
- ✅ Runs Alembic migrations
- ✅ Starts backend with hot reload
- ✅ Starts frontend with hot reload

### Default Test Account

```
Email: admin@test.com
Password: Admin123!
```

See [DOCKER_SETUP.md](DOCKER_SETUP.md) for detailed documentation.

## Features

### AI-Powered Stock Analysis
- Expert financial analyst persona with GPT-5 via TheSys.dev
- RAG-enhanced context retrieval from conversation history (pgvector)
- Real-time streaming responses via Server-Sent Events
- LangChain agent with 7 specialized tools for market data

### Portfolio Management
- **Transaction Management** - Full audit trail with BUY/SELL/DIVIDEND/TRANSFER_IN/TRANSFER_OUT/ADJUSTMENT types, atomic holdings sync
- **CSV Import** - Bulk import holdings from spreadsheets with preview and duplicate detection
- **Portfolio Analytics Dashboard** - Real-time metrics, charts, and analytics
  - Portfolio value over time (line chart)
  - Allocation breakdown (pie chart)
  - Gains/losses by holding (bar chart)
  - Performance metrics (total return, gain/loss summary)
- **VWAP Auto-Fill** - Automatically fetches Volume-Weighted Average Price for purchase dates

### Multi-Currency Support
- **4 Currencies**: EUR, GBP, CHF, USD
- **Historical Exchange Rates** - Charts use accurate rates from each date (not just today's rate)
- **yfinance Forex Data** - Fetches rates from EURUSD=X, GBPUSD=X, etc.
- **LRU Caching** - 500-entry cache for performance
- **Inverse Pair Fallback** - Handles all currency combinations

### Authentication
- JWT-based authentication with refresh tokens
- Email/password registration and login
- OAuth infrastructure ready (Google/GitHub)
- Password reset flow with emailed tokens
- Profile management (change email, password, preferred currency, country)
- Protected routes and API endpoints

### Market Data Tools
- **Stock Prices** - Current and historical OHLCV data
- **Financials** - Balance sheet and fundamental data
- **News** - Latest articles and press releases
- **Company Logos** - Visual branding for holdings
- **Currency Conversion** - Real-time exchange rates between EUR, GBP, CHF, USD
- **VWAP Calculator** - Volume-Weighted Average Price for any ticker on any date

### Dashboard
- **Central Hub** - Landing page with quick navigation to chat, portfolio, and profile
- **User Profile** - Account settings (email, password change, preferred currency, country)

## Technology Stack

### Backend
- **Framework**: FastAPI (async web framework)
- **Database**: PostgreSQL 16 with pgvector extension
- **Cache**: Redis with RediSearch (semantic caching via LangCache)
- **ORM**: SQLAlchemy 2.0 with async support
- **Migrations**: Alembic
- **AI/ML**:
  - LangChain (agentic AI framework with `create_agent`)
  - ChatOpenAI (GPT-5 via TheSys.dev API)
  - OpenAI Embeddings (RAG via pgvector)
- **Data**: yfinance (Yahoo Finance - stocks, forex, historical data)
- **Auth**: JWT tokens with refresh + bcrypt password hashing + OAuth (Google/GitHub)
- **Logging**: Loguru (structured logging with rotation)
- **Async Workers**: BackgroundTasks for context storage
- **Observability**: Prometheus metrics for RAG performance and cache hit rates

### Frontend
- **Framework**: React 19 with TypeScript
- **Build Tool**: Vite
- **Routing**: React Router v7
- **HTTP Client**: axios with JWT interceptor and auto-refresh
- **State Management**: React Context (auth), TanStack React Query (data fetching), Zustand
- **UI Libraries**:
  - @thesysai/genui-sdk (C1Chat component)
  - Shadcn/ui components (Radix primitives + TailwindCSS)
  - Recharts (portfolio charts)
  - Framer Motion (animations)
  - Sonner (toast notifications)
  - React Hook Form + Zod (form validation)
- **Testing**: Vitest + React Testing Library

### Infrastructure
- **Containerization**: Docker Compose (4 services)
- **Services**: postgres, redis, backend, frontend
- **Hot Reload**: Both backend (Uvicorn) and frontend (Vite)

## Project Structure

```
stockanalysis/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── core/                # Config, database, security, cache
│   │   ├── routers/             # API endpoints (auth, chat, portfolio)
│   │   ├── services/            # Business logic
│   │   │   ├── currency_service.py      # Real-time & historical forex
│   │   │   ├── portfolio_service.py     # Holdings CRUD
│   │   │   └── portfolio_performance_service.py  # Charts & metrics
│   │   ├── agents/              # LangChain agent configuration
│   │   ├── tools/               # Stock data tools (price, news, etc.)
│   │   └── models/              # SQLAlchemy & Pydantic models
│   ├── alembic/                 # Database migrations
│   └── pyproject.toml           # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── pages/               # Route components
│   │   │   ├── ChatPage.tsx     # AI chat interface
│   │   │   ├── PortfolioPage.tsx
│   │   │   └── DashboardPage.tsx
│   │   ├── components/          # Reusable UI components
│   │   │   ├── portfolio/       # Charts, tables, forms
│   │   │   └── ui/              # Shadcn components
│   │   ├── context/             # Auth context
│   │   └── services/            # API client
│   └── package.json
│
├── docker-compose.yml           # 4-service stack
├── CLAUDE.md                    # Developer guide
└── docs/                        # Documentation
```

## Architecture

### Backend Architecture

**Modular Package Structure** (backend/app/):
- `main.py` - FastAPI app entry with CORS, lifespan, middleware, router includes, Prometheus metrics
- `core/` - Config (pydantic-settings), database (SQLAlchemy), security (JWT), cache (LangCache/Redis), logging (Loguru)
- `routers/` - auth (register, login, OAuth, profile), chat (streaming + RAG), portfolio (holdings, transactions, analytics), market_data (VWAP)
- `services/` - Business logic: auth, portfolio CRUD, portfolio performance, transactions (atomic), CSV import, currency (forex), OAuth, email, embeddings, context storage/retrieval
- `agents/` - LangChain agent creation with 7 tools
- `tools/` - Stock price, historical price, balance sheet, news, company logo, currency converter
- `models/` - SQLAlchemy ORM models (User, Holding, Transaction, ConversationHistory, PortfolioSnapshot, PasswordResetToken) + Pydantic schemas
- `middleware/` - Logging middleware with correlation IDs

**API Router Prefixes**:
- `/api/auth/*` - Authentication and user management
- `/api/chat` - Streaming chat with RAG
- `/api/portfolio/*` - Holdings, transactions, chart data, CSV import
- `/api/market-data/*` - VWAP and market data lookups
- `/metrics` - Prometheus metrics endpoint

**Agent Tools** (7):
1. `get_stock_price(ticker, user_currency)` - Current stock price with currency conversion
2. `get_historical_stock_price(ticker, start_date, end_date, user_currency)` - Historical OHLCV data
3. `get_balance_sheet(ticker, user_currency)` - Financial statement data
4. `get_stock_news(ticker)` - Recent news articles
5. `get_company_logo(ticker)` - Company logo URL
6. `convert_currency(amount, from_currency, to_currency)` - Currency conversion
7. `get_exchange_rate(from_currency, to_currency)` - Exchange rate lookup

**RAG Data Flow**:
1. User sends message via frontend
2. Backend retrieves relevant context from pgvector (semantic search via OpenAI embeddings)
3. Context injected into system prompt for awareness
4. LangChain agent processes query with 7 available tools
5. Tools fetch data (yfinance, forex) with automatic currency conversion
6. Agent generates response using GPT-5 via TheSys.dev
7. Response streamed back to frontend (plain text, not SSE formatted)
8. Conversation turn stored in PostgreSQL via background task (non-blocking)

### Frontend Architecture

**Page Structure** (React Router v7):
- Public: Login, Signup, Forgot Password, Reset Password, OAuth Callback
- Protected (JWT required): Dashboard, Chat, Portfolio, Portfolio Dashboard, Profile

**Component Structure**:
- Chat interface delegates to C1Chat component from GenUI SDK (with custom `processMessage` for JWT injection)
- Portfolio views use Recharts (line, pie, bar charts) with currency-aware data
- Profile management forms with React Hook Form + Zod validation
- Layout with AppLayout component, page transitions via Framer Motion

**Communication**:
- axios instance with interceptor for automatic JWT token refresh
- Custom `processMessage` function injects JWT from localStorage (bypasses axios for streaming)
- Vite dev server proxies `/api` requests to backend during development
- Toast notifications via Sonner

## Local Development Setup

### Prerequisites

- Python 3.10 or higher
- Node.js 18+ and npm
- Git

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies using uv:
```bash
pip install uv
uv sync
```

Alternatively, use pip:
```bash
pip install -r requirements.txt  # If you have one
# Or install manually:
pip install fastapi uvicorn langchain langchain-openai pydantic python-dotenv yfinance loguru tiktoken
```

4. Create a `.env` file in the backend directory:
```env
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.thesys.dev/v1/embed/
OPENAI_MODEL=c1/openai/gpt-5/v-20250930
```

5. Create the logs directory:
```bash
mkdir -p logs
```

6. Start the backend server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8888
```

The backend will be available at `http://localhost:8888`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install --legacy-peer-deps
```

3. Start the development server (stop the Docker `frontend` service first - both use port 3000):
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

### Accessing the Application

1. Open your browser and navigate to `http://localhost:3000`
2. The chat interface will load with dark theme
3. Start asking questions about stocks:
   - "What's the current price of AAPL?"
   - "Analyze Tesla's financial health"
   - "Compare MSFT and GOOGL"
   - "Show me NVDA's historical performance over the last year"

## API Reference

### Authentication (`/api/auth`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Register new user (email, password, currency, country) |
| POST | `/login` | Login, returns access + refresh tokens |
| POST | `/refresh` | Refresh access token |
| GET | `/me` | Get current authenticated user info |
| POST | `/forgot-password` | Request password reset email |
| POST | `/reset-password` | Reset password with token |
| POST | `/change-password` | Change password (authenticated) |
| POST | `/change-email` | Change email address |
| POST | `/change-currency` | Update preferred currency |
| POST | `/change-country` | Update country |
| GET | `/oauth/google` | Initiate Google OAuth flow |
| GET | `/oauth/google/callback` | Google OAuth callback |
| GET | `/oauth/github` | Initiate GitHub OAuth flow |
| GET | `/oauth/github/callback` | GitHub OAuth callback |

### Chat (`/api/chat`)

**POST /api/chat** - Streaming AI stock analysis with RAG

Requires authentication via JWT Bearer token.

**Request Body**:
```json
{
  "prompt": {
    "content": "string",     // User's message
    "id": "string",          // Unique message ID
    "role": "user"           // Message role
  },
  "threadId": "string",      // Conversation thread identifier
  "responseId": "string"     // Response identifier
}
```

**Response**: Plain text streaming (Content-Type: `text/plain`). Tokens yielded in real-time.

**POST /api/chat/debug** - Debug endpoint to inspect raw request data.

### Portfolio (`/api/portfolio`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/holdings` | List all holdings with current prices |
| GET | `/holdings/{id}` | Get single holding details |
| GET | `/summary` | Portfolio summary (total value, gain/loss, return %) |
| GET | `/allocation` | Allocation breakdown for pie chart |
| GET | `/gains-losses` | Per-holding gain/loss for bar chart |
| GET | `/historical-value` | Portfolio value over time for line chart |
| POST | `/snapshot` | Create daily portfolio value snapshot |
| POST | `/transactions` | Create transaction (BUY/SELL/DIVIDEND/TRANSFER_IN/TRANSFER_OUT/ADJUSTMENT) |
| GET | `/transactions` | Filterable transaction history |
| GET | `/transactions/{id}` | Get specific transaction |
| PUT | `/transactions/{id}` | Update transaction (atomic holdings adjust) |
| DELETE | `/transactions/{id}` | Delete transaction (reverses holdings effect) |
| POST | `/import/preview` | Preview CSV import with validation |
| POST | `/import/confirm` | Execute CSV import after confirmation |

All portfolio endpoints require authentication. All support `?currency=EUR|GBP|CHF|USD` parameter.

### Market Data (`/api/market-data`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/vwap/{ticker}` | Get VWAP for ticker on specific date (query: `?date=YYYY-MM-DD`) |

### Infrastructure

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root - API info |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics (RAG performance, cache rates) |

## Configuration

### Environment Variables (.env)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | API key for GPT-5 via TheSys.dev |
| `OPENAI_EMBEDDINGS_API_KEY` | No | - | OpenAI API key for embeddings (RAG) |
| `MODEL_NAME` | No | `c1/openai/gpt-5/v-20250930` | LLM model identifier |
| `MODEL_BASE_URL` | No | `https://api.thesys.dev/v1/embed/` | LLM API base URL |
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `REDIS_URL` | No | - | Redis connection string (caching) |
| `SECRET_KEY` | Yes | - | JWT signing key (`openssl rand -hex 32`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | JWT access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | JWT refresh token TTL |
| `CORS_ORIGINS` | No | `http://localhost:3000,http://localhost:5173` | Allowed CORS origins |
| `FRONTEND_URL` | No | `http://localhost:3000` | Frontend URL for OAuth redirects |
| `GOOGLE_CLIENT_ID` | No | - | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | No | - | Google OAuth client secret |
| `GITHUB_CLIENT_ID` | No | - | GitHub OAuth client ID |
| `GITHUB_CLIENT_SECRET` | No | - | GitHub OAuth client secret |
| `LOG_LEVEL` | No | `INFO` | Log level (DEBUG/INFO/WARNING/ERROR) |
| `LOG_FORMAT` | No | `text` | Log format (`text` or `json`) |

### Token Limits (configured in code)
- `TOKEN_LIMIT` - Maximum tokens per conversation (250,000)
- `WARNING_THRESHOLD` - Warning threshold (200,000)
- `MAX_HISTORY_MESSAGES` - Maximum messages to keep (20)

### Logging Configuration
- Log file: `backend/logs/app.log`
- Rotation: 500 MB
- Retention: 10 days
- Level: Configurable via `LOG_LEVEL`

### Frontend Configuration

**Vite Proxy** (vite.config.ts):
```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8888',
    changeOrigin: true
  }
}
```

**TypeScript**:
- Strict mode enabled
- Unused variables/parameters detection
- ES2020 target

## Development Commands

### Backend

```bash
# Start development server with auto-reload
uvicorn main:app --reload

# Run in production mode
uvicorn main:app --host 0.0.0.0 --port 8888

# Check syntax
python -m py_compile main.py

# Run with specific log level
uvicorn main:app --log-level debug
```

### Frontend

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linter
npm run lint
```

## Logging

The application uses structured logging with Loguru:

**Log Locations**:
- Console output (stdout)
- File: `backend/logs/app.log`

**Log Entries Include**:
- Application startup/shutdown
- API request details (thread ID, message preview)
- Token counts per message
- Tool usage (ticker symbols, data retrieved)
- Errors with full stack traces

**Example Log Entry**:
```
2024-12-13 02:20:39.832 | INFO | __main__:chat:130 - Received chat request - Thread ID: b953f479-b846-4298-a027-3797598ee85c, Message: What's the price of AAPL?...
2024-12-13 02:20:39.833 | INFO | __main__:chat:136 - Current message tokens: 12
2024-12-13 02:20:40.156 | INFO | __main__:get_stock_price:59 - Getting stock price for ticker: AAPL
2024-12-13 02:20:40.892 | INFO | __main__:get_stock_price:62 - Stock price for AAPL: $175.43
```

## Error Handling

**Token Limit Errors**:
- Caught and displayed to user with clear message
- Suggests clearing conversation to continue
- Logged for monitoring

**API Errors**:
- Graceful error messages returned to user
- Full error details logged
- Prevents application crashes

**Tool Errors**:
- Invalid ticker symbols handled
- Data unavailability communicated clearly
- Fallback responses provided

## Known Limitations

1. **LangCache Requires RediSearch** - Semantic caching depends on Redis with RediSearch module; falls back silently without it
2. **No WebSocket Support** - Chat uses SSE streaming (unidirectional), not full-duplex WebSockets
3. **No Rate Limiting** - API endpoints don't have rate limiting yet
4. **Token Limits** - Long conversations may hit per-conversation token limits
5. **OAuth Not Configured** - Google/GitHub OAuth infrastructure exists but requires API keys in .env
6. **No Email Verification** - SMTP configuration required for email verification and password reset
7. **Single Region Focus** - Exchange rates default to USD base; designed for US/EU markets
8. **Historical Forex Dependency** - Exchange rate data depends on yfinance availability

## Security Considerations

**Current Implementation**:
- JWT authentication with access/refresh tokens
- Password hashing with bcrypt
- Protected API endpoints with dependency injection
- API keys in .env file (excluded from git)
- Input validation via Pydantic

**Production Requirements**:
- Restrict CORS to specific origins
- Add rate limiting
- Enable HTTPS
- Configure OAuth providers
- Add email verification

## Quick Commands

```bash
# Start everything
docker-compose up

# View logs
docker-compose logs -f backend

# Run database migration
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Install frontend package
docker-compose exec -T frontend npm install <package> --legacy-peer-deps
docker-compose restart frontend

# Access database
docker-compose exec postgres psql -U stockanalysis -d stockanalysis

# Stop everything
docker-compose down

# Nuclear reset
docker-compose down -v && docker-compose up --build
```

## Contributing

See [CLAUDE.md](CLAUDE.md) for the developer guide with architecture details, patterns, and critical rules.

## Acknowledgments

- Market data from Yahoo Finance via yfinance
- AI powered by GPT-5 via TheSys.dev
- UI components from TheSys.ai GenUI SDK and Shadcn/ui

## Troubleshooting

**Docker containers won't start**:
```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs backend
docker-compose logs frontend

# Rebuild from scratch
docker-compose down -v
docker-compose up --build
```

**Frontend missing dependencies**:
```bash
docker-compose exec -T frontend npm install --legacy-peer-deps
docker-compose restart frontend
```

**Database connection errors**:
```bash
# Wait for postgres to be healthy, then restart backend
docker-compose restart backend
```

**Chat returns 401 Unauthorized**:
- Clear localStorage and log in again
- Check that JWT token is being sent in Authorization header

**Portfolio charts show wrong currency values**:
- Verify user's preferred_currency in profile
- Check backend logs for exchange rate fetch errors

**No response from AI chat**:
- Verify OPENAI_API_KEY is set in .env
- Check backend logs for API errors
- Ensure TheSys.dev API quota is not exceeded

See [EPIC.md](EPIC.md) for full specifications and [STATUS.md](STATUS.md) for detailed progress.
