# 🩺 Watsonx Medical MCP Server

> A Python-based MCP “agent” that wraps **IBM watsonx.ai** to deliver conversational and medical-symptom analysis tools for watsonx Orchestrate.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![License Apache-2.0](https://img.shields.io/badge/license-Apache%202.0-blue)]()

---

## 🚀 Features

* **MCP protocol** support over **STDIO** (ready for MCP Gateway auto-discovery)
* Two production-ready tools

  * `chat_with_watsonx`: general chat powered by watsonx.ai
  * `analyze_medical_symptoms`: preliminary medical assessment
* **Conversation management** helpers (`get_conversation_summary`, `clear_conversation_history`)
* **Resources & prompts** for greetings, server info, and structured medical consultation
* **Zero-downtime** dev reloads possible via `uvicorn --reload` (if you migrate to HTTP)
* **Makefile workflow** for linting, formatting, testing, Docker, and more
* **Unit tests** with pytest—CI-ready
* Fully containerised with a lightweight Dockerfile

---

## 📦 Project Structure

```text
watsonx-medical-mcp-server/
├── Makefile                  # Development workflow
├── Dockerfile                # Container image
├── requirements.txt          # Python deps
├── server.py                 # FastMCP stdio server
├── .env.example              # Copy to .env and set creds
├── test/
│   └── test_server.py        # Simple smoke test
├── assets/
│   └── 2025-06-30-22-15-29.png
└── README.md                 # You are here
```

---

## ⚙️ Prerequisites

| Requirement                          | Notes                                  |
| ------------------------------------ | -------------------------------------- |
| **Python 3.11+**                     | Local development                      |
| **IBM watsonx.ai** credentials       | `API Key`, `Service URL`, `Project ID` |
| (Optional) **Docker** & **GNU Make** | Containerised workflows                |

---

## 🛠️ Setup & Local Development

1. **Clone the repo**

   ```bash
   git clone https://github.com/ruslanmv/watsonx-medical-mcp-server.git
   cd watsonx-medical-mcp-server
   ```

2. **Create & activate a virtual environment**

   ```bash
   make setup               # creates .venv & installs deps
   source .venv/bin/activate
   ```

3. **Configure environment variables**

   ```bash
   cp .env.example .env
   # then edit .env:
   # WATSONX_APIKEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   # WATSONX_URL=https://us-south.ml.cloud.ibm.com
   # PROJECT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   # MODEL_ID=meta-llama/llama-3-2-90b-vision-instruct
   ```



4. **Run the agent (STDIO MCP server)**

   ```bash
   make run
   ```

   The server now speaks MCP on stdin/stdout.

5. **Quick smoke test**

   ```bash
   python test/test_server.py
   ```

   ![](assets/2025-06-30-22-15-29.png)

---

## ⚙️ Makefile Targets

```text
make setup         # Create / update .venv & install deps
make run           # Start stdio-based MCP server
make lint          # Run flake8
make fmt           # Format code with Black
make test          # Run pytest suite
make check         # lint + fmt + test
make docker-build  # Build Docker image
make docker-run    # Run containerised server
make clean-stamp   # Force reinstall deps without deleting .venv
make clean         # Remove .venv
```

---

## 🐳 Docker

1. **Build**

   ```bash
   make docker-build
   ```

2. **Run**

   ```bash
   make docker-run
   ```

   The container reads your `.env`, launches `server.py`, and communicates via STDIO.
   Mount volumes or expose ports as needed.

---

## 🔗 Registering in MCP Gateway

1. **Start MCP Gateway** (e.g., `docker compose up` for the reference implementation).

2. **Add the server**

   *Via Admin UI*

   * Navigate to **Catalog → Servers → Add Server**
   * **Transport**: `STDIO`
   * **Command**: `/full/path/to/.venv/bin/python`
   * **Args**: `["/full/path/to/server.py"]`
   * Enable **Auto-discover tools** and save.

   *Via REST API*

   ```bash
   curl -X POST http://localhost:4444/servers \
     -H "Authorization: Bearer <ADMIN_JWT>" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "watsonx-medical-assistant",
       "transport": "stdio",
       "command": "/app/.venv/bin/python",
       "args": ["/app/server.py"],
       "autoDiscover": true
     }'
   ```

---

## ✅ Testing & Continuous Integration

* **Run tests locally**

  ```bash
  make test
  ```

* **Code coverage**

  ```bash
  pytest --cov=.
  ```

* **Pre-commit hooks**

  ```bash
  pre-commit install
  ```

---

## 📜 License

Licensed under the **Apache 2.0** license. See [LICENSE](LICENSE) for full text.

Made with ❤️ and a dose of science to help users find reliable information—remember, this agent is **not a substitute for professional medical advice**.
