"""
Shared pytest fixtures and configuration for all tests.

This file contains fixtures that mock external API calls to ensure:
- Zero cost (no real API calls to OpenAI, yfinance, etc.)
- Fast execution (no network latency)
- Deterministic results (same data every time)
"""

import pytest
from unittest.mock import MagicMock
import pandas as pd


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

    mocker.patch("app.agents.stock_analyst.agent", mock_agent)

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
def fastapi_test_client():
    """Create a test client for FastAPI integration tests."""
    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app)
