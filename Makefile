# LineAgent Project Makefile
# Centralized build and development commands

.PHONY: help clean-all test test-verbose test-module gradio-deploy start-demo-server stop-demo-server build-package publish-pypi publish-testpypi create-venv run-chat

help:
	@echo "Lineagentic-Composer Project"
	@echo ""
	@echo "Available commands:"
	@echo "  - create-venv: Create virtual environment and install dependencies"
	@echo "  - run-chat: Create virtual environment and run chat.py (CLI interface)"
	@echo "  - start-demo-server: Start Gradio web interface (gradio_chat.py)"
	@echo "  - stop-demo-server: Stop the Gradio web interface"
	@echo "  - start-all-services: Start all services"
	@echo "  - stop-all-services: Stop all services"
	@echo "  - stop-all-services-and-clean-data: Stop all services and clean data"
	@echo "  - clean-all-stack: Clean all stack"
	@echo "  - test: Run all tests"
	@echo "  - test-agent-manager: Run agent manager tests"
	@echo "  - test-framework-agent: Run framework agent tests"
	@echo "  - test-verbose: Run all tests with verbose output"
	@echo "  - test-module: Run specific test module (e.g., make test-module MODULE=test_agent_manager)"
	@echo "  - gradio-deploy: Deploy to Hugging Face Spaces using Gradio"
	@echo "  - build-package: Build the PyPI package"
	@echo "  - publish-testpypi: Publish to TestPyPI (sandbox)"
	@echo "  - publish-pypi: Publish to PyPI (production)"

# Load environment variables from .env file
ifneq (,$(wildcard .env))
    include .env
    export
endif


create-venv:
	@echo " Creating virtual environment..."
	@if command -v uv >/dev/null 2>&1; then \
		echo " Using uv for dependency management..."; \
		uv sync; \
		uv pip install -e .; \
	elif command -v python3 >/dev/null 2>&1; then \
		echo " Using standard Python tools..."; \
		python3 -m venv .venv; \
		. .venv/bin/activate && pip install --upgrade pip; \
		. .venv/bin/activate && pip install -e .; \
	else \
		echo " Error: Neither uv nor python3 found. Please install Python 3.8+ or uv."; \
		exit 1; \
	fi
	@echo " Virtual environment created successfully!"

# Run chat.py in virtual environment
run-chat:
	@echo "Starting chat application in virtual environment..."
	@$(MAKE) create-venv
	@echo "Launching chat interface..."
	@. .venv/bin/activate && python chat.py

# =============================================================================
# DEMO SERVER


# Start demo server
start-demo-server:
	@echo "Running python gradio_chat.py with virtual environment activated..."
	@$(MAKE) create-venv
	@if pgrep -f "python.*gradio_chat.py" > /dev/null; then \
		echo "  Demo server is already running!"; \
		echo "   Use 'make stop-demo-server' to stop it first"; \
	else \
		. .venv/bin/activate && python gradio_chat.py > /dev/null 2>&1 & \
		echo " Demo server starting in background..."; \
		echo " Waiting for server to be ready..."; \
		while ! curl -s http://localhost:7860 > /dev/null 2>&1; do \
			echo "   Waiting for server to start..."; \
			sleep 2; \
		done; \
		echo " Server is now running and available at http://localhost:7860"; \
		echo " Use 'make stop-demo-server' to stop the demo server"; \
	fi

# Stop demo server
stop-demo-server:
	@echo " Stopping demo server..."
	@pkill -f "python.*gradio_chat.py" || echo "No demo server process found"
	@lsof -ti:7860 | xargs kill -9 2>/dev/null || echo "No process on port 7860"
	@echo " Demo server stopped"

# =============================================================================
# CLEANUP COMMANDS ############################################################
# =============================================================================

# Remove all __pycache__ directories
clean-pycache:
	@echo "  Removing all __pycache__ directories..."
	@echo " Searching for __pycache__ directories..."
	@find . -type d -name "__pycache__" -print
	@echo "  Removing found directories..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + || echo "Error removing some directories"
	@echo " Verifying removal..."
	@if find . -type d -name "__pycache__" 2>/dev/null | grep -q .; then \
		echo "  Some __pycache__ directories still exist:"; \
		find . -type d -name "__pycache__" 2>/dev/null; \
	else \
		echo " All __pycache__ directories removed successfully!"; \
	fi

# Clean up temporary files and kill processes
clean-all:
	@echo "🧹 Cleaning up temporary files and processes..."
	@echo " Killing processes on ports 7860..."
	@lsof -ti:7860 | xargs kill -9 2>/dev/null || echo "No process on port 7860"
	@echo " Cleaning up temporary files..."
	@find . -name "*.log" -type f -delete
	@find . -name "temp_*.json" -type f -delete
	@find . -name "generated-*.json" -type f -delete
	@echo " Removing data folders..."
	@rm -rf agents_log 2>/dev/null || echo "No agents_log folder found"
	@rm -rf .venv 2>/dev/null || echo "No .venv folder found"
	@rm -rf demo-deploy 2>/dev/null || echo "No demo-deploy folder found"
	@rm -rf lineagentic_flow.egg-info 2>/dev/null || echo "No lineagentic_flow.egg-info folder found"
	@rm -rf demo-venv 2>/dev/null || echo "No demo-venv folder found"
	@rm -rf lineagentic_composer.egg-info 2>/dev/null || echo "No lineagentic_composer.egg-info folder found"
	@rm -rf .pytest_cache 2>/dev/null || echo "No .pytest_cache folder found"
	@rm -rf .mypy_cache 2>/dev/null || echo "No .mypy_cache folder found"
	@rm -rf logs 2>/dev/null || echo "No logs folder found"
	@rm -rf .ruff_cache 2>/dev/null || echo "No .ruff_cache folder found"
	@rm -rf dist 2>/dev/null || echo "No dist folder found"
	@rm -rf logs 2>/dev/null || echo "No logs folder found"
	@rm -rf demo-deploy 2>/dev/null || echo "No demo-deploy folder found"
	@find . -name "*.log" -type f -delete 2>/dev/null || echo "No .log files found"
	@find . -name "*.json" -type f -delete 2>/dev/null || echo "No .json files found"
	@$(MAKE) clean-pycache
	@rm -rf venv 2>/dev/null || echo "No venv folder found"
	@echo " Cleanup completed!"


# =============================================================================
# GRADIO COMMANDS ############################################################
# =============================================================================

# Deploy to Hugging Face Spaces using Gradio
gradio-deploy:
	@echo "🚀 Preparing Lineagentic-DPC Gradio deployment..."
	@sleep 2
	@echo "📁 Creating demo-deploy directory..."
	@rm -rf demo-deploy
	@mkdir demo-deploy
	@echo "📦 Copying necessary files..."
	@cp demo/demo_server.py demo-deploy/
	@cp demo/start_demo_server.py demo-deploy/
	@cp demo/deploy_setup.py demo-deploy/
	@cp demo/requirements-deploy.txt demo-deploy/requirements.txt
	@echo "📁 Copying package files for local installation..."
	@cp pyproject.toml demo-deploy/
	@echo "📁 Copying Lineagentic-DPC project files..."
	@cp -r dp_chat_agent demo-deploy/
	@cp -r dp_composer_server demo-deploy/
	@echo "✅ Files copied to demo-deploy/"
	@echo "🌐 Deploying with Gradio..."
	@cd demo-deploy && gradio deploy --app-file start_demo_server.py
	@echo "✅ Lineagentic-DPC Gradio deployment completed!"


# =============================================================================
# PYPI PACKAGE COMMANDS ######################################################
# =============================================================================

# Build the PyPI package
build-package:
	@echo "📦 Building PyPI package..."
	@echo "🧹 Cleaning previous builds..."
	@rm -rf dist build *.egg-info
	@echo "🔨 Building package..."
	@python -m build
	@echo "Package built successfully!"
	@echo "Package files created in dist/ directory"
	@echo "Next steps:"
	@echo "  - Test locally: pip install dist/lineagentic_flow-0.1.0.tar.gz"
	@echo "  - Publish to TestPyPI: make publish-testpypi"
	@echo "  - Publish to PyPI: make publish-pypi"

# Publish to PyPI (production)
publish-pypi:
	@echo "Publishing to PyPI (production)..."
	@if [ ! -d "dist" ]; then \
		echo " No dist/ directory found. Run 'make build-package' first."; \
		exit 1; \
	fi
	@echo "WARNING: This will publish to production PyPI!"
	@echo "   Make sure you have tested on TestPyPI first."
	@read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo " Checking package..."
	@python -m twine check dist/*
	@echo " Uploading to PyPI..."
	@python -m twine upload dist/*
	@echo "Package published to PyPI!"
	@echo "View at: https://pypi.org/project/lineagentic-flow/"
	@echo "Install with: pip install lineagentic-flow"

