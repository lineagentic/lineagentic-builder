#!/bin/bash

# Data Product Scoping Agent Gradio App Launcher (UV Version)
echo "🚀 Launching Data Product Scoping Agent Gradio App with UV..."

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Error: OPENAI_API_KEY environment variable is not set"
    echo "Please set it before running the app:"
    echo "export OPENAI_API_KEY='your-api-key-here'"
    exit 1
fi

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed or not in PATH"
    echo "Please install uv: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# Check if pyproject.toml exists
if [ ! -f "pyproject_gradio.toml" ]; then
    echo "❌ Error: pyproject_gradio.toml not found"
    echo "Please ensure you're in the correct directory"
    exit 1
fi

# Install dependencies if needed
echo "📦 Checking and installing dependencies with UV..."
uv sync --project pyproject_gradio.toml

# Launch the app using uv run
echo "🎯 Starting the app with UV..."
uv run --project pyproject_gradio.toml python gradio_scoping_app.py
