# Makefile for watsonx-medical-mcp-server
#
# Improvements:
# - Checks for python3.11 before running.
# - Interactively asks to reuse or reinstall the existing '.venv'.
# - Added 'help', 'reinstall', and 'check-format' targets for better usability.
# - General cleanup and adherence to best practices.

.PHONY: all setup install run lint format check-format test check docker-build docker-run clean reinstall help

# ==============================================================================
# Configuration
# ==============================================================================

# Default Python version
PYTHON_VERSION ?= 3.11

# Project variables
VENV           := .venv
STAMP          := $(VENV)/.install_complete
PYTHON_VENV    := $(VENV)/bin/python

# ==============================================================================
# System Checks
# ==============================================================================

# Find the required Python interpreter on the system. Exit with an error if not found.
PYTHON_SYSTEM := $(shell command -v python$(PYTHON_VERSION))
ifeq ($(PYTHON_SYSTEM),)
    $(error Python $(PYTHON_VERSION) is not installed or not in your PATH. Aborting.)
endif

# ==============================================================================
# Core Targets
# ==============================================================================

# Default target: Set up the environment
all: setup

# Self-documenting help target
help:
	@echo "Makefile for watsonx-medical-mcp-server"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Core Targets:"
	@echo "  setup          - Interactively set up the Python virtual environment. The default target."
	@echo "  reinstall      - Force re-creation of the virtual environment and install dependencies."
	@echo "  run            - Run the MCP server."
	@echo ""
	@echo "Quality & Testing:"
	@echo "  lint           - Check code style with flake8."
	@echo "  format         - Format code with black."
	@echo "  check-format   - Check if code is formatted, without modifying files."
	@echo "  test           - Run tests with pytest."
	@echo "  check          - Run all checks: lint, check-format, and test."
	@echo ""
	@echo "Docker:"
	@echo "  docker-build   - Build the Docker image."
	@echo "  docker-run     - Run the Docker container (requires .env file)."
	@echo ""
	@echo "Cleanup:"
	@echo "  clean          - Remove the virtual environment and cache files."


# This rule uses a stamp file to avoid reinstalling dependencies if they are already up-to-date.
# It only runs if 'requirements.txt' is newer than the stamp file or if the stamp file doesn't exist.
$(STAMP): requirements.txt
	@echo "📦 Installing/updating dependencies..."
	@$(PYTHON_VENV) -m pip install --upgrade pip
	@$(PYTHON_VENV) -m pip install --no-cache-dir -r requirements.txt
	@touch $(STAMP)
	@echo "✅ Dependencies are up to date."

# Alias for dependency installation
install: $(STAMP)

# Interactive setup of the virtual environment
setup:
	@if [ -d "$(VENV)" ]; then \
		echo "✅ Virtual environment '$(VENV)' already exists."; \
		printf "   Would you like to reinstall it? [y/N] "; \
		read -r answer; \
		if [ "$$answer" = "y" ] || [ "$$answer" = "Y" ]; then \
			$(MAKE) reinstall; \
		else \
			echo "   Reusing existing environment. Checking dependencies..."; \
			$(MAKE) install; \
		fi \
	else \
		echo "🔧 Creating new virtual environment..."; \
		$(PYTHON_SYSTEM) -m venv $(VENV); \
		$(MAKE) install; \
	fi

# Force reinstallation of venv and dependencies
reinstall: clean
	@echo "🔧 Re-creating virtual environment in $(VENV)..."
	@$(PYTHON_SYSTEM) -m venv $(VENV)
	@$(MAKE) install

# ==============================================================================
# Development & QA Targets
# ==============================================================================

# Run the MCP server
run: setup
	@echo "🚀 Starting Watsonx Medical MCP Server…"
	@$(PYTHON_VENV) server.py

# Static analysis with flake8
lint: setup
	@echo "🔍 Running flake8..."
	@$(PYTHON_VENV) -m flake8 .

# Code formatting with Black (modifies files)
format: setup
	@echo "🎨 Formatting code with black..."
	@$(PYTHON_VENV) -m black .

# Check code formatting with Black (does not modify files)
check-format: setup
	@echo "🎨 Checking code formatting with black..."
	@$(PYTHON_VENV) -m black --check .

# Run pytest on the test suite
test: setup
	@echo "🧪 Running tests..."
	@$(PYTHON_VENV) -m pytest -q test/test_server.py

# Composite target to run all checks
check: lint check-format test

# ==============================================================================
# Docker Targets
# ==============================================================================

# Build Docker image
docker-build:
	@echo "🐳 Building Docker image watsonx-medical-mcp-server:latest…"
	@docker build -t watsonx-medical-mcp-server:latest .

# Run Docker container
docker-run:
	@echo "🐳 Running Docker container..."
	@docker run --rm -it \
		--env-file .env \
		--name watsonx-medical-mcp-server \
		watsonx-medical-mcp-server:latest

# ==============================================================================
# Cleanup Target
# ==============================================================================

# Remove the virtual environment and other generated files
clean:
	@echo "🧹 Removing virtual environment and cache files..."
	@rm -rf $(VENV) .pytest_cache .mypy_cache __pycache__ **/__pycache__
	@echo "✅ Cleanup complete."