# Makefile for watsonx-medical-mcp-server
#
# Features
# --------
# • Verifies that Python 3.11 is installed.
# • Creates/updates an isolated virtual-env in `.venv`.
# • Convenient `lint` target that runs **both** Flake8 and `black --check`.
# • Separate `format` and `check-format` targets for full control.
# • Composite `check` target that runs style checks **and** tests.
# • Docker helpers, clean-up, and a built-in help screen.

.PHONY: \
    all help \
    setup install reinstall clean \
    run lint format check-format test check \
    docker-build docker-run

# ==============================================================================
# Configuration
# ==============================================================================

# Required Python version
PYTHON_VERSION ?= 3.11

# Paths inside the repo
VENV        := .venv
STAMP       := $(VENV)/.install_complete
PYTHON_VENV := $(VENV)/bin/python

# ==============================================================================
# System Checks
# ==============================================================================

PYTHON_SYSTEM := $(shell command -v python$(PYTHON_VERSION))
ifeq ($(PYTHON_SYSTEM),)
    $(error Python $(PYTHON_VERSION) is not installed or not in your PATH. Aborting.)
endif

# ==============================================================================
# Core Targets
# ==============================================================================

all: setup

help:
	@echo "Makefile for watsonx-medical-mcp-server"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Core:"
	@echo "  setup          Interactively set up the Python virtual environment (default)."
	@echo "  reinstall      Wipe and recreate the virtual environment."
	@echo "  run            Run the MCP server."
	@echo ""
	@echo "Quality & Testing:"
	@echo "  lint           Run Flake8 *and* black --check."
	@echo "  format         Reformat the codebase with black."
	@echo "  check-format   Verify black formatting only (no Flake8)."
	@echo "  test           Run the pytest suite."
	@echo "  check          Run lint + tests (CI green-light)."
	@echo ""
	@echo "Docker:"
	@echo "  docker-build   Build the Docker image."
	@echo "  docker-run     Run the Docker container (requires .env)."
	@echo ""
	@echo "Cleanup:"
	@echo "  clean          Remove the virtual environment and cache files."

# ==============================================================================
# Virtual-env & Dependencies
# ==============================================================================

$(STAMP): requirements.txt
	@echo "📦 Installing/updating dependencies…"
	@$(PYTHON_VENV) -m pip install --upgrade pip
	@$(PYTHON_VENV) -m pip install --no-cache-dir -r requirements.txt
	@$(PYTHON_VENV) -m pip install --no-cache-dir flake8 black pytest
	@touch $(STAMP)
	@echo "✅ Dependencies are up to date."

install: $(STAMP)

setup:
	@if [ -d "$(VENV)" ]; then \
		echo "✅ Virtual environment '$(VENV)' already exists."; \
		printf "   Reinstall it? [y/N] "; \
		read -r answer; \
		if [ "$$answer" = "y" ] || [ "$$answer" = "Y" ]; then \
			$(MAKE) reinstall; \
		else \
			echo "   Reusing existing environment. Checking dependencies…"; \
			$(MAKE) install; \
		fi \
	else \
		echo "🔧 Creating new virtual environment…"; \
		$(PYTHON_SYSTEM) -m venv $(VENV); \
		$(MAKE) install; \
	fi

reinstall: clean
	@echo "🔧 Re-creating virtual environment in $(VENV)…"
	@$(PYTHON_SYSTEM) -m venv $(VENV)
	@$(MAKE) install

# ==============================================================================
# Development & QA Targets
# ==============================================================================

run: setup
	@echo "🚀 Starting Watsonx Medical MCP Server…"
	@$(PYTHON_VENV) server.py

## ──────────────────────────────────────────────────────────────────────────── ##
##  Quality gates
## ──────────────────────────────────────────────────────────────────────────── ##

lint: setup
	@echo "🔍 Running flake8…"
	@$(PYTHON_VENV) -m flake8 .
	@echo "🎨 Verifying Black formatting…"
	@$(PYTHON_VENV) -m black --check .

format: setup
	@echo "🎨 Formatting code with black…"
	@$(PYTHON_VENV) -m black .

check-format: setup
	@echo "🎨 Checking code formatting with black…"
	@$(PYTHON_VENV) -m black --check .

test: setup
	@echo "🧪 Running tests…"
	@WATSONX_APIKEY=dummy_api_key_for_testing PROJECT_ID=dummy_project_id_for_testing \
		$(PYTHON_VENV) -m pytest -v test/

check: lint test

# ==============================================================================
# Docker
# ==============================================================================

docker-build:
	@echo "🐳 Building Docker image watsonx-medical-mcp-server:latest…"
	@docker build -t watsonx-medical-mcp-server:latest .

docker-run:
	@echo "🐳 Running Docker container…"
	@docker run --rm -it \
		--env-file .env \
		--name watsonx-medical-mcp-server \
		watsonx-medical-mcp-server:latest

# ==============================================================================
# Cleanup
# ==============================================================================

clean:
	@echo "🧹 Removing virtual environment and cache files…"
	@rm -rf $(VENV) .pytest_cache .mypy_cache __pycache__ **/__pycache__
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete."
