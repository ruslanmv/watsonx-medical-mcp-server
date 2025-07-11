# Makefile for watsonx-medical-mcp-server
.PHONY: all setup run lint fmt test check docker-build docker-run clean clean-stamp

# Configuration
PYTHON_VERSION ?= 3.11
VENV            := .venv
STAMP           := $(VENV)/.setup_complete
PYTHON          := $(VENV)/bin/python
PIP             := $(VENV)/bin/pip

# Default target: ensure virtual environment is ready
all: setup

# Stamp file: recreate venv & install deps whenever requirements.txt changes
$(STAMP): requirements.txt
	@echo "🔧 (Re)creating virtual environment ($(PYTHON_VERSION)) in $(VENV)…"
	@python$(PYTHON_VERSION) -m venv $(VENV)
	@$(PIP) install --upgrade pip
	@$(PIP) install --no-cache-dir -r requirements.txt
	@touch $(STAMP)
	@echo "✅ Virtual environment is ready."

# Alias for venv setup
setup: $(STAMP)

# Force reinstallation of deps without deleting venv
clean-stamp:
	@echo "🗑️  Removing stamp file to force reinstall…"
	@rm -f $(STAMP)

# Run the MCP server under uvicorn (or stdio)
run: setup
	@echo "🚀 Starting Watsonx Medical MCP Server…"
	@$(PYTHON) server.py

# Static analysis with flake8
lint: setup
	@echo "🔍 Running flake8…"
	@$(VENV)/bin/flake8 .

# Code formatting with Black
fmt: setup
	@echo "🎨 Running black…"
	@$(VENV)/bin/black .

# Run pytest on the test suite
test: setup
	@echo "🧪 Running pytest on test/test_server.py…"
	@$(VENV)/bin/pytest -q test/test_server.py

# Composite target: lint, format-check, and tests
check: lint fmt test

# Build Docker image
docker-build:
	@echo "🐳 Building Docker image watsonx-medical-mcp-server:latest…"
	@docker build -t watsonx-medical-mcp-server:latest .

# Run Docker container (make sure you have a .env file)
docker-run:
	@echo "🐳 Running Docker container…"
	@docker run --rm -it \
		--env-file .env \
		--name watsonx-medical-mcp-server \
		watsonx-medical-mcp-server:latest

# Remove the virtual environment entirely
clean:
	@echo "🧹 Removing virtual environment…"
	@rm -rf $(VENV)

