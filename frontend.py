"""
frontend.py – Flask web interface for the Watsonx Medical Assistant.

The heavy lifting (talking to `server.py` through MCP) is handled by
backend.py.  This file focuses purely on HTTP routes, session handling,
and HTML rendering.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import List, Dict

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

# Markdown support
import markdown  # pip install markdown
from markupsafe import Markup


# ---------------------------------------------------------------------------
# Backend helpers
# ---------------------------------------------------------------------------

from backend import get_mcp_response, parse_message_for_action  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration & Flask setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Frontend] %(levelname)s: %(message)s",
)

app = Flask(__name__)
# IMPORTANT: replace for production
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-replace-me")

MAX_HISTORY_CHARS = 4_000  # ~1000 tokens, adjust if needed

# Markdown support
# ONE-LINE FILTER ⤵
app.jinja_env.filters["md"] = lambda text: Markup(
    markdown.markdown(text, extensions=["fenced_code"])
)

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def trim_history(history: List[Dict[str, str]], max_chars: int) -> List[Dict[str, str]]:
    """
    Ensure session history stays below *max_chars* by evicting the oldest
    entries (but always keep at least 2 messages so the chat makes sense).
    """
    current_chars = sum(len(msg.get("content", "")) for msg in history)

    while current_chars > max_chars and len(history) > 2:
        removed = history.pop(0)
        current_chars -= len(removed.get("content", ""))
        logging.info("Trimmed chat history to %d characters.", current_chars)

    return history


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    """Chat home page."""
    if "history" not in session:
        session["history"] = []
        welcome = (
            "🤖 Welcome to Watsonx Medical Assistant! I can help you with:\n\n"
            "• General health questions\n"
            "• Medical symptom analysis\n"
            "• Health information\n\n"
            "Try typing 'symptoms: [your symptoms]' for medical analysis, or just ask me anything!"
        )
        session["history"].append({"role": "assistant", "content": welcome})

    return render_template("chat.html", history=session["history"])


@app.route("/chat", methods=["POST"])
def chat():
    """Handle a standard chat POST from the form."""
    user_message = request.form.get("message", "").strip()
    if not user_message:
        return redirect(url_for("index"))

    session.setdefault("history", []).append({"role": "user", "content": user_message})

    action, kwargs = parse_message_for_action(user_message)
    bot_text, error = get_mcp_response(action, **kwargs)

    if error:
        session["history"].append({"role": "error", "content": error})
    else:
        if action == "analyze_symptoms":
            bot_text = (
                "🏥 **Medical Analysis:**\n\n"
                f"{bot_text}\n\n"
                "⚠️ *This is for informational purposes only. "
                "Please consult a healthcare professional for proper medical advice.*"
            )
        session["history"].append({"role": "assistant", "content": bot_text})

    session["history"] = trim_history(session["history"], MAX_HISTORY_CHARS)
    session.modified = True
    return redirect(url_for("index"))


@app.route("/clear")
def clear_chat():
    """Clear chat history in session and on the backend."""
    get_mcp_response("clear_history")
    session.pop("history", None)
    logging.info("Chat history cleared.")
    return redirect(url_for("index"))


@app.route("/summary")
def get_summary():
    """Get a conversation summary from the backend."""
    session.setdefault("history", [])
    summary, error = get_mcp_response("get_summary")

    if error:
        session["history"].append(
            {"role": "error", "content": f"Summary error: {error}"}
        )
    else:
        content = (
            f"📋 **Conversation Summary:**\n\n{summary}"
            if summary
            else "📋 No conversation to summarise yet."
        )
        session["history"].append({"role": "assistant", "content": content})

    session.modified = True
    return redirect(url_for("index"))


@app.route("/analyze_symptoms", methods=["POST"])
def analyze_symptoms():
    """Dedicated form for structured symptom analysis."""
    symptoms = request.form.get("symptoms", "").strip()
    age = request.form.get("age", "").strip()
    gender = request.form.get("gender", "").strip()

    if not symptoms:
        return redirect(url_for("index"))

    session.setdefault("history", [])
    user_input = f"Symptoms: {symptoms}"
    kwargs: Dict[str, str | int] = {"symptoms": symptoms}

    if age:
        try:
            kwargs["age"] = int(age)
            user_input += f", Age: {age}"
        except ValueError:
            pass
    if gender:
        kwargs["gender"] = gender
        user_input += f", Gender: {gender}"

    session["history"].append({"role": "user", "content": user_input})

    bot_text, error = get_mcp_response("analyze_symptoms", **kwargs)
    if error:
        session["history"].append({"role": "error", "content": error})
    else:
        formatted = (
            "🏥 **Medical Analysis:**\n\n"
            f"{bot_text}\n\n"
            "⚠️ *This is for informational purposes only. "
            "Please consult a healthcare professional for proper medical advice.*"
        )
        session["history"].append({"role": "assistant", "content": formatted})

    session["history"] = trim_history(session["history"], MAX_HISTORY_CHARS)
    session.modified = True
    return redirect(url_for("index"))


@app.route("/server_info")
def server_info():
    """Display basic info exposed by the backend server."""
    session.setdefault("history", [])
    info, error = get_mcp_response("get_server_info")

    if error:
        session["history"].append(
            {"role": "error", "content": f"Server info error: {error}"}
        )
    else:
        content = (
            f"ℹ️ **Server Information:**\n\n{info}"
            if info
            else "ℹ️ Server information not available."
        )
        session["history"].append({"role": "assistant", "content": content})

    session.modified = True
    return redirect(url_for("index"))


@app.route("/greeting/<name>")
def get_greeting(name: str):
    """Personalized greeting fetched from the backend."""
    session.setdefault("history", [])
    greeting, error = get_mcp_response("get_greeting", name=name)

    if error:
        session["history"].append(
            {"role": "error", "content": f"Greeting error: {error}"}
        )
    else:
        content = (
            f"👋 {greeting}"
            if greeting
            else f"👋 Hello {name}! Welcome to the Medical Assistant."
        )
        session["history"].append({"role": "assistant", "content": content})

    session.modified = True
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# JSON API endpoints
# ---------------------------------------------------------------------------


@app.route("/api/chat", methods=["POST"])
def api_chat():
    payload = request.get_json(force=True, silent=True) or {}
    message = payload.get("message", "").strip()
    if not message:
        return jsonify({"error": "No message provided."}), 400

    action, kwargs = parse_message_for_action(message)
    reply, error = get_mcp_response(action, **kwargs)

    if error:
        return jsonify({"error": error, "success": False}), 500
    return jsonify({"response": reply, "action": action, "success": True})


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    data = request.get_json(force=True, silent=True) or {}
    symptoms = data.get("symptoms", "").strip()
    if not symptoms:
        return jsonify({"error": "No symptoms provided."}), 400

    kwargs: Dict[str, str | int] = {"symptoms": symptoms}
    if "age" in data:
        kwargs["age"] = data["age"]
    if "gender" in data:
        kwargs["gender"] = data["gender"]

    analysis, error = get_mcp_response("analyze_symptoms", **kwargs)
    if error:
        return jsonify({"error": error, "success": False}), 500
    return jsonify({"analysis": analysis, "success": True})


# ---------------------------------------------------------------------------
# Misc / help
# ---------------------------------------------------------------------------


@app.route("/help")
def help_page():
    """Static help text dropped into the chat history."""
    session.setdefault("history", [])
    # Whitespace has been removed from the end of the lines below
    help_text = """
🤖 **Watsonx Medical Assistant Help**

**Available Features:**
• **General Chat**: Ask me any health-related questions
• **Symptom Analysis**: Get preliminary medical assessments
• **Health Information**: Learn about conditions and treatments

**How to Use:**
• **Regular Chat**: Just type your question normally
• **Symptom Analysis**: Type "symptoms: [your symptoms]" or use the dedicated form
• **Clear History**: Click "Clear Chat" to start fresh
• **Get Summary**: Click "Summary" for a quick recap

⚠️  This assistant provides *general* information only.
⚠️  Always consult healthcare professionals for medical advice.
⚠️  In emergencies, contact emergency services immediately.
    """
    session["history"].append({"role": "assistant", "content": help_text})
    session.modified = True
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Error handlers & template vars
# ---------------------------------------------------------------------------


@app.errorhandler(404)
def not_found_error(error):  # noqa: ANN001
    return (
        render_template("error.html", error_code=404, error_message="Page not found"),
        404,
    )


@app.errorhandler(500)
def internal_error(error):  # noqa: ANN001
    return (
        render_template(
            "error.html", error_code=500, error_message="Internal server error"
        ),
        500,
    )


@app.context_processor
def inject_template_vars():
    return {"app_name": "Watsonx Medical Assistant", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Quick sanity-check so devs don’t forget the backend stub.
    if not os.path.exists("server.py"):
        print("ERROR: server.py not found in the current directory!")
        sys.exit(1)

    print("🚀 Starting Watsonx Medical Assistant Web Interface…")
    print("🌐 Visit: http://localhost:5001")
    print("📖 For usage instructions open /help")

    # Use waitress/gunicorn in production
    app.run(debug=True, host="0.0.0.0", port=5001)
