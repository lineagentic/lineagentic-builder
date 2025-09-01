#!/bin/bash

# Data Product Scoping Agent Gradio App Launcher
echo "🚀 Launching Data Product Scoping Agent Gradio App..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed or not in PATH"
    exit 1
fi

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed or not in PATH"
    echo "Please install uv: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

# Check if pyproject_gradio.toml exists and sync dependencies
if [ -f "pyproject_gradio.toml" ]; then
    echo "📦 Syncing dependencies with UV..."
    uv sync --project pyproject_gradio.toml
else
    echo "⚠️  pyproject_gradio.toml not found, proceeding without dependency sync"
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating template..."
    cat > .env << EOF
# OpenAI API Configuration
OPENAI_API_KEY=your-openai-api-key-here

# Optional: Model Configuration
DEFAULT_MODEL=gpt-4o-mini

# Optional: Server Configuration
GRADIO_SERVER_PORT=7860
GRADIO_SERVER_NAME=0.0.0.0
EOF
    echo "✅ Created .env template. Please edit it with your actual API key."
    echo "Then run this script again."
    exit 1
fi

# Load environment variables from .env file
echo "📋 Loading environment variables from .env file..."
export $(grep -v '^#' .env | xargs)

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your-openai-api-key-here" ]; then
    echo "❌ Error: OPENAI_API_KEY not properly set in .env file"
    echo "Please edit .env file and set your actual OpenAI API key"
    exit 1
fi

echo "✅ Environment loaded successfully"
echo "🔑 Using model: ${DEFAULT_MODEL:-gpt-4o-mini}"

# Launch the app
echo "🎯 Starting the app..."
python3 gradio_scoping_app.py
