# ────────────────────────────────────────────────────────────────
#  🐳 Dockerfile — watsonx-medical-mcp-server
#  Builds a lightweight container that runs server.py via STDIO
# ────────────────────────────────────────────────────────────────

# 1️⃣ Base image – slim Python 3.11
FROM python:3.11-slim AS base

# 2️⃣ Environment settings
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# 3️⃣ Workdir inside the container
WORKDIR /app

# 4️⃣ Install build tooling (gcc et al. may be needed by some deps)
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# 5️⃣ Dependency layer – copy only requirements first for better cache
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6️⃣ Copy the rest of the source code
COPY . .

# 7️⃣ Create an unprivileged user and switch to it
RUN addgroup --system app && \
    adduser  --system --ingroup app --home /app --shell /usr/sbin/nologin appuser
USER appuser

# 8️⃣ Default execution: speak MCP via STDIO
ENTRYPOINT ["python", "server.py"]

# 9️⃣ (Optional) Healthcheck — verifies the process is alive
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD pgrep -f "python server.py" || exit 1

# ────────────────────────────────────────────────────────────────
# Build:  docker build -t watsonx-medical-mcp-server:latest .
# Run:    docker run --rm -it --env-file .env watsonx-medical-mcp-server:latest
# ────────────────────────────────────────────────────────────────
