#!/bin/bash

# Run the Scoping Agent Chat App with uv

echo "🚀 Starting Scoping Agent Chat App..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install uv first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found."
    echo "   The app will run with mock responses."
    echo "   To use real OpenAI API:"
    echo "   1. Copy env.example to .env: cp env.example .env"
    echo "   2. Edit .env and add your OpenAI API key"
fi

# Check if OPENAI_API_KEY is set in .env
if [ -f ".env" ] && ! grep -q "OPENAI_API_KEY=your-openai-api-key-here" .env; then
    echo "✅ .env file found with API key"
else
    echo "⚠️  Please set your OpenAI API key in .env file"
fi

# Install dependencies with uv
echo "📦 Installing dependencies with uv..."
uv sync

# Run the chat app
echo "🤖 Launching Gradio chat app..."
uv run python gradio_chat_app.py
