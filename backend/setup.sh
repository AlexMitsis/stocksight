#!/bin/bash
# Setup script for Stock Analysis Backend

echo "🔧 Setting up Stock Analysis Backend..."

# Install dependencies
echo "📦 Installing dependencies..."
uv sync

# Install package in editable mode
echo "🔗 Installing package in editable mode..."
uv pip install -e .

echo "✅ Setup complete!"
echo ""
echo "To run the server:"
echo "  uv run python run.py"
echo ""
echo "Or:"
echo "  uv run uvicorn app.main:app --host 0.0.0.0 --port 8888 --reload"
