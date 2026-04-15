# Stock Analysis Backend

AI-powered stock analysis and investment assistant API built with FastAPI and LangChain.

## Quick Start

### Prerequisites

- Python 3.10+
- uv (Python package manager)
- OpenAI API key

### Installation

```bash
# Install dependencies
uv sync

# Install the package in editable mode (required for imports to work)
uv pip install -e .
```

### Configuration

Create a `.env` file with your API key:

```env
OPENAI_API_KEY=your-api-key-here
```

### Running the Server

**Option 1: Using the convenience script (recommended)**
```bash
uv run python run.py
```

**Option 2: Using uvicorn directly**
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8888 --reload
```

**Option 3: Using python -m**
```bash
uv run python -m uvicorn app.main:app --host 0.0.0.0 --port 8888 --reload
```

The server will start at `http://localhost:8888`

## API Endpoints

### Health Check
```bash
GET /health
```
Response: `{"status": "healthy"}`

### Root
```bash
GET /
```
Response: `{"message": "Stock Analysis API", "version": "1.0.0"}`

### Chat (Streaming)
```bash
POST /api/chat
Content-Type: application/json

{
  "prompt": {
    "content": "What is the price of AAPL?",
    "id": "msg-1",
    "role": "user"
  },
  "threadId": "thread-123",
  "responseId": "resp-1"
}
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app initialization
│   ├── agents/              # Agent configurations
│   │   └── stock_analyst.py # Stock analyst agent
│   ├── core/                # Core configurations
│   │   ├── config.py        # Environment settings
│   │   ├── constants.py     # Application constants
│   │   └── logging.py       # Logging configuration
│   ├── models/              # Pydantic models
│   │   └── chat.py          # Chat request/response models
│   ├── routers/             # API route handlers
│   │   └── chat.py          # Chat endpoint
│   ├── tools/               # LangChain tools
│   │   ├── stock_price.py
│   │   ├── historical_price.py
│   │   ├── balance_sheet.py
│   │   ├── news.py
│   │   └── company_logo.py
│   └── utils/               # Utility functions
│       └── token_counter.py # Token counting
├── tests/                   # Test suite (coming in Story 1.2)
├── logs/                    # Application logs
├── run.py                   # Convenience run script
├── pyproject.toml           # Dependencies
└── .env                     # Environment variables (create this)
```

## Available Tools

The stock analyst agent has access to:

1. **get_stock_price** - Current stock prices
2. **get_historical_stock_price** - Historical price data for trend analysis
3. **get_balance_sheet** - Company financial statements
4. **get_stock_news** - Latest news and press releases
5. **get_company_logo** - Company branding/logos

## Development

### Adding a New Tool

1. Create a new file in `app/tools/`
2. Define your tool using the `@tool` decorator
3. Import and add it to the agent in `app/agents/stock_analyst.py`

### Adding a New Endpoint

1. Create a new router in `app/routers/`
2. Define your endpoints
3. Include the router in `app/main.py`

## Testing

```bash
# Run tests (coming in Story 1.2)
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=xml
```

## Configuration

Environment variables (set in `.env`):

- `OPENAI_API_KEY` - Your OpenAI API key (required)
- `MODEL_NAME` - Model to use (default: `c1/openai/gpt-5/v-20250930`)
- `MODEL_BASE_URL` - API base URL (default: `https://api.thesys.dev/v1/embed/`)
- `HOST` - Server host (default: `0.0.0.0`)
- `PORT` - Server port (default: `8888`)

## Logging

Logs are written to:
- Console (stdout/stderr)
- `logs/app.log` (rotating, 500MB max, 10 days retention)

## Architecture

This backend follows a clean architecture pattern:

- **Routers**: Handle HTTP requests/responses
- **Agents**: Configure LangChain agents with tools
- **Tools**: Individual functions for data retrieval
- **Models**: Pydantic models for validation
- **Core**: Configuration and shared utilities
- **Utils**: Helper functions (token counting, etc.)

## Troubleshooting

### Permission Denied Error

If you see "Permission denied (os error 13)", make sure you're using the new command:
```bash
uv run python run.py
```

NOT the old command:
```bash
uv run python main.py  # ❌ This won't work anymore
```

### Module Import Errors

Make sure you're in the `backend/` directory and have run:
```bash
uv sync
```

### API Key Errors

Ensure your `.env` file exists and contains a valid `OPENAI_API_KEY`.

## Migration from Old Structure

If you were using the old single-file `main.py`:
- It's been backed up as `main.py.backup`
- Update your run commands to use `app.main:app`
- All functionality remains the same

## Next Steps

- [ ] Story 1.2: Add unit tests with pytest
- [ ] Story 1.5: Add PostgreSQL database
- [ ] Story 1.6: Add Docker Compose setup
- [ ] Story 2.1: Add Pinecone vector database

## License

[Add your license here]
