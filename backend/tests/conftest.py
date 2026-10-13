"""
Shared pytest fixtures and configuration for all tests.

This file contains fixtures that mock external API calls to ensure:
- Zero cost (no real API calls to OpenAI, yfinance, etc.)
- Fast execution (no network latency)
- Deterministic results (same data every time)
"""

import hashlib
import math
import os
import re

import pytest
from unittest.mock import MagicMock
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

# Point the app at a dedicated test database BEFORE any app module is imported
# (app.core.config reads DATABASE_URL once at import time).
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL must be set to a Postgres database ending in '_test'")
if not make_url(TEST_DATABASE_URL).database.endswith("_test"):
    raise RuntimeError(f"Refusing to run tests against non-test database: {TEST_DATABASE_URL}")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


@pytest.fixture(scope="session", autouse=True)
def test_database():
    """Create the test database if needed and migrate it to the latest schema."""
    from alembic import command
    from alembic.config import Config

    url = make_url(TEST_DATABASE_URL)
    admin_engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin_engine.dispose()

    command.upgrade(Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini")), "head")


DB_FIXTURES = {"db_session", "test_users", "fastapi_test_client", "client"}


@pytest.fixture(autouse=True)
def clean_tables(request):
    """Empty all tables after each test that uses the database (via one of DB_FIXTURES)."""
    yield
    if not DB_FIXTURES.intersection(request.fixturenames):
        return
    from app.core.database import Base, engine

    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture(autouse=True)
def disable_redis_cache(monkeypatch):
    """Run tools uncached so results don't depend on whether a Redis server is reachable.
    Cache tests install their own mock client on top of this."""
    monkeypatch.setattr("app.core.cache.redis_client", None)


@pytest.fixture(autouse=True)
def reset_service_singletons():
    """Drop cached service instances so a mock captured by one test can't leak into the next."""
    yield
    import app.services.context_retrieval_service as retrieval
    import app.services.context_storage_service as storage
    import app.services.embedding_service as embedding

    retrieval._context_retrieval_service = None
    storage._context_storage_service = None
    embedding._embedding_service = None


@pytest.fixture
def db_session():
    """SQLAlchemy session bound to the test database."""
    from app.core.database import SessionLocal

    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def mock_yfinance_ticker(mocker):
    """
    Mock yfinance.Ticker to avoid real Yahoo Finance API calls.

    Returns a mock that simulates typical yfinance responses.
    """
    mock_ticker = MagicMock()

    # Mock stock.history() for current price
    mock_history = pd.DataFrame(
        {
            "Close": [175.43],
            "Open": [174.50],
            "High": [176.20],
            "Low": [173.80],
            "Volume": [50000000],
        }
    )
    mock_ticker.history.return_value = mock_history

    # Mock stock.info for company data
    mock_ticker.info = {
        "longName": "Apple Inc.",
        "shortName": "Apple",
        "symbol": "AAPL",
        "marketCap": 2800000000000,
        "sector": "Technology",
    }

    # Mock stock.balance_sheet
    mock_balance_sheet = pd.DataFrame(
        {
            "Total Assets": [352755000000],
            "Total Liabilities": [287912000000],
            "Stockholders Equity": [64843000000],
            "Cash And Cash Equivalents": [48304000000],
            "Total Debt": [132480000000],
        }
    )
    mock_ticker.balance_sheet = mock_balance_sheet

    # Mock stock.news
    mock_ticker.news = [
        {
            "title": "Apple Reports Record Q4 Earnings",
            "publisher": "Reuters",
            "link": "https://example.com/news1",
            "providerPublishTime": 1699564800,
        },
        {
            "title": "iPhone 15 Sales Exceed Expectations",
            "publisher": "Bloomberg",
            "link": "https://example.com/news2",
            "providerPublishTime": 1699478400,
        },
    ]

    # Patch yfinance.Ticker globally
    mocker.patch("yfinance.Ticker", return_value=mock_ticker)

    return mock_ticker


def _fake_embedding(text: str) -> list:
    """Deterministic bag-of-words vector: texts sharing words get similar embeddings."""
    vec = [0.0] * 1536
    vec[0] = 1.0  # never all-zero (cosine distance is undefined for zero vectors)
    for word in re.findall(r"\w+", text.lower()):
        vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % 1536] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec]


@pytest.fixture(autouse=True)
def fake_embeddings(request, mocker):
    """
    Replace OpenAI embedding calls with _fake_embedding so tests never hit the paid API.

    Tests marked `quality` measure real retrieval accuracy and keep real embeddings;
    they are deselected by default and run explicitly with `pytest -m quality`.
    """
    if request.node.get_closest_marker("quality"):
        return

    async def aembed_query(self, text):
        return _fake_embedding(text)

    async def aembed_documents(self, texts, *args, **kwargs):
        return [_fake_embedding(t) for t in texts]

    mocker.patch("langchain_openai.OpenAIEmbeddings.aembed_query", aembed_query)
    mocker.patch("langchain_openai.OpenAIEmbeddings.aembed_documents", aembed_documents)
    mocker.patch(
        "langchain_openai.OpenAIEmbeddings.embed_query", lambda self, text: _fake_embedding(text)
    )
    mocker.patch(
        "langchain_openai.OpenAIEmbeddings.embed_documents",
        lambda self, texts, *a, **k: [_fake_embedding(t) for t in texts],
    )


@pytest.fixture
def mock_historical_data():
    """Mock historical stock data for date range queries."""
    return pd.DataFrame(
        {
            "Close": [170.0, 172.0, 175.0, 173.0, 175.43],
            "Open": [169.0, 171.0, 174.0, 172.0, 174.50],
            "High": [171.0, 173.0, 176.0, 174.0, 176.20],
            "Low": [168.0, 170.0, 173.0, 171.0, 173.80],
            "Volume": [45000000, 47000000, 50000000, 48000000, 50000000],
        },
        index=pd.date_range(start="2024-01-01", periods=5, freq="D"),
    )


@pytest.fixture(autouse=True)
def mock_openai_client(mocker):
    """
    Auto-mock OpenAI API responses to avoid costs.

    This ensures NO real LLM API calls during tests.
    Applied to all tests automatically.
    """
    # Mock the OpenAI client creation
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Mocked AI response"

    # Mock ChatOpenAI to prevent any real API calls
    mocker.patch("langchain_openai.ChatOpenAI")

    return mock_client


@pytest.fixture
def sample_chat_request():
    """Sample chat request payload for testing."""
    return {
        "prompt": {"content": "What is the price of AAPL?", "id": "test-msg-1", "role": "user"},
        "threadId": "test-thread-123",
        "responseId": "test-resp-1",
    }


@pytest.fixture
def mock_langchain_messages():
    """Mock LangChain message objects for testing."""
    from langchain.messages import SystemMessage, HumanMessage, AIMessage

    return {
        "system": SystemMessage("You are a helpful assistant"),
        "human": HumanMessage("What is the price of AAPL?"),
        "ai": AIMessage("The price of AAPL is $175.43"),
    }


@pytest.fixture
def mock_agent(mocker):
    """
    Mock the LangChain agent to avoid real LLM calls.

    This is crucial for integration tests.
    """
    mock_agent = MagicMock()
    mock_agent.stream.return_value = iter(
        [
            (MagicMock(content="The "), None),
            (MagicMock(content="price "), None),
            (MagicMock(content="is "), None),
            (MagicMock(content="$175.43"), None),
        ]
    )

    # chat.py does `from app.agents.stock_analyst import agent`, so patch its reference
    mocker.patch("app.routers.chat.agent", mock_agent)

    return mock_agent


@pytest.fixture
def test_settings(monkeypatch):
    """Override settings for testing."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-12345")
    monkeypatch.setenv("MODEL_NAME", "test-model")
    monkeypatch.setenv("MODEL_BASE_URL", "https://test.example.com")
    monkeypatch.setenv("HOST", "localhost")
    monkeypatch.setenv("PORT", "8888")


@pytest.fixture
def test_users(db_session):
    """Users with ids 1 and 2, for tests that reference user_id directly."""
    from app.models.database import User

    users = [User(email=f"user{i}@test.com", hashed_password="not-a-real-hash") for i in (1, 2)]
    db_session.add_all(users)
    db_session.commit()
    for user in users:
        db_session.refresh(user)
        db_session.expunge(user)  # usable from the TestClient thread without this session
    return users


@pytest.fixture
def fastapi_test_client(test_users):
    """Test client for FastAPI integration tests, authenticated as user 1."""
    from fastapi.testclient import TestClient
    from app.core.security import get_current_active_user
    from app.main import app

    app.dependency_overrides[get_current_active_user] = lambda: test_users[0]
    yield TestClient(app)
    app.dependency_overrides.clear()
