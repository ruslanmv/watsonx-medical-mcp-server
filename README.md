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


## 🛠️ Setup & Local Development

Getting the server running locally is straightforward. This project requires **Python 3.11**.

1.  **Clone the Repository**

    ```bash
    git clone https://github.com/ruslanmv/watsonx-medical-mcp-server.git
    cd watsonx-medical-mcp-server
    ```

2.  **Set Up the Environment**
    Run the interactive setup command. It will create a virtual environment (`.venv`) and install all dependencies.

    ```bash
    make setup
    ```

    The script will detect if you have an existing environment and ask if you want to reuse or reinstall it.

3.  **Activate the Environment**
    To run commands manually (like `python server.py`), you'll need to activate the environment in your shell.

    ```bash
    source .venv/bin/activate
    ```

    **Note**: You don't need to do this when using `make` targets like `make run` or `make test`, as they handle it automatically.

4.  **Configure Environment Variables**
    Create a `.env` file from the example and add your IBM Watsonx credentials.

    ```bash
    cp .env.example .env
    ```

    Now, edit the `.env` file with your details:

    ```ini
    # .env
    WATSONX_APIKEY="your_api_key_here"
    PROJECT_ID="your_project_id_here"

    # Optional: Change the default model or URL
    # WATSONX_URL="https://us-south.ml.cloud.ibm.com"
    # MODEL_ID="meta-llama/llama-3-2-90b-vision-instruct"
    ```

5.  **Run the Server**
    Start the server, which will communicate over STDIO (standard input/output).

    ```bash
    make run
    ```

6.  **Run a Quick Test**
    To confirm everything is working, run the test suite.

    ```bash
    make test
    ```

    This command will send a test query to your running server and verify the connection.

-----

## ⚙️ Makefile Targets

The `Makefile` provides several commands to streamline development. You can view this list anytime by running `make help`.

```text
Makefile for watsonx-medical-mcp-server

Usage: make <target>

Core Targets:
  setup            - Interactively set up the Python virtual environment. The default target.
  reinstall        - Force re-creation of the virtual environment and install dependencies.
  run              - Run the MCP server.

Quality & Testing:
  lint             - Check code style with flake8.
  format           - Format code with black.
  check-format     - Check if code is formatted, without modifying files.
  test             - Run tests with pytest.
  check            - Run all checks: lint, check-format, and test.

Docker:
  docker-build     - Build the Docker image.
  docker-run       - Run the Docker container (requires .env file).

Cleanup:
  clean            - Remove the virtual environment and cache files.
```

-----


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
