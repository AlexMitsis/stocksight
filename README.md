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

## Quick Start with Docker 🐳

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
- LangChain agent with 5 specialized tools for market data

### Portfolio Management
- **Holdings Tracking** - Add/edit/delete stock holdings with purchase dates
- **CSV Import** - Bulk import holdings from spreadsheets
- **Performance Dashboard** - Real-time metrics, charts, and analytics
  - Portfolio value over time (line chart)
  - Allocation breakdown (pie chart)
  - Gains/losses by holding (bar chart)
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
- Protected routes and API endpoints

### Market Data Tools
- **Stock Prices** - Current and historical OHLCV data
- **Financials** - Balance sheet and fundamental data
- **News** - Latest articles and press releases
- **Company Logos** - Visual branding for holdings

## Technology Stack

### Backend
- **Framework**: FastAPI (async web framework)
- **Database**: PostgreSQL 16 with pgvector extension
- **Cache**: Redis with RediSearch
- **ORM**: SQLAlchemy 2.0 with async support
- **Migrations**: Alembic
- **AI/ML**:
  - LangChain (agentic AI framework)
  - LangGraph (workflow orchestration)
  - ChatOpenAI (GPT-5 via TheSys.dev API)
- **Data**: yfinance (Yahoo Finance - stocks, forex, historical data)
- **Auth**: JWT tokens with refresh mechanism
- **Logging**: Loguru (structured logging with rotation)

### Frontend
- **Framework**: React 19 with TypeScript
- **Build Tool**: Vite
- **UI Libraries**:
  - @thesysai/genui-sdk (C1Chat component)
  - Shadcn/ui components
  - Recharts (portfolio charts)
  - TailwindCSS
- **State**: React Context for auth

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

**Single-File Application** (main.py):
- FastAPI application setup with CORS middleware
- LangChain agent configuration with GPT-5
- Five tool definitions for market data retrieval
- In-memory conversation checkpointer
- Token counting and logging infrastructure
- Streaming response generator

**API Endpoints**:
- `POST /api/chat` - Main chat endpoint with SSE streaming

**Agent Tools**:
1. `get_stock_price(ticker)` - Current stock price
2. `get_historical_stock_price(ticker, start_date, end_date)` - Historical OHLCV data
3. `get_balance_sheet(ticker)` - Financial statement data
4. `get_stock_news(ticker)` - Recent news articles
5. `get_company_logo(ticker)` - Company logo URL

**Data Flow**:
1. User sends message via frontend
2. Backend receives request with thread ID for conversation continuity
3. Token count logged for monitoring
4. LangChain agent processes query and selects appropriate tools
5. Tools fetch data from Yahoo Finance or logo services
6. Agent generates response using GPT-5
7. Response streamed back to frontend via SSE
8. Conversation state saved in memory checkpointer

### Frontend Architecture

**Component Structure**:
- Minimal React application leveraging pre-built UI components
- Delegates chat interface to C1Chat component from genui-sdk
- ThemeProvider for dark theme management

**Communication**:
- Direct API calls to `/api/chat` endpoint
- Handles streaming responses from backend
- Vite dev server proxies requests during development

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
npm install
```

3. Start the development server:
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

### POST /api/chat

Main chat endpoint for conversational stock analysis.

**Request Body**:
```json
{
  "prompt": {
    "content": "string",     // User's message
    "id": "string",          // Unique message ID
    "role": "string"         // Message role (user/assistant)
  },
  "threadId": "string",      // Conversation thread identifier
  "responseId": "string"     // Response identifier
}
```

**Response**:
- Server-Sent Events (SSE) stream
- Content-Type: `text/event-stream`
- Streams response tokens in real-time

**Headers**:
- Cache-Control: `no-cache, no-transform`
- Connection: `keep-alive`

## Configuration

### Backend Configuration

**Environment Variables** (.env):
- `OPENAI_API_KEY` - Your OpenAI/TheSys API key
- `OPENAI_BASE_URL` - API base URL (default: https://api.thesys.dev/v1/embed/)
- `OPENAI_MODEL` - Model identifier (default: c1/openai/gpt-5/v-20250930)

**Token Limits** (in main.py):
- `TOKEN_LIMIT` - Maximum tokens per conversation (250,000)
- `WARNING_THRESHOLD` - Warning threshold (200,000)
- `MAX_HISTORY_MESSAGES` - Maximum messages to keep (20)

**Logging Configuration**:
- Log file: `logs/app.log`
- Rotation: 500 MB
- Retention: 10 days
- Level: INFO

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

1. **No Rate Limiting**: API endpoints don't have rate limiting yet
2. **Token Limits**: Long conversations may hit token limits
3. **OAuth Not Configured**: Google/GitHub OAuth infrastructure exists but requires API keys
4. **No Email Verification**: User registration doesn't verify email addresses
5. **Single Region**: Exchange rates default to USD base; designed for US/EU markets

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
