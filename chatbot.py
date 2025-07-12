# chatbot.py
# Frontend + Backend
# Single code
import os
import sys
import asyncio
import logging
import json
import threading
import atexit
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import markdown              # pip install markdown
from markupsafe import Markup
# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [Frontend] %(levelname)s: %(message)s')

# --- Flask App Setup ---
app = Flask(__name__)

# IMPORTANT: Change this to a random secret key for production!
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-replace-me")

# --- Conversation Memory Configuration ---
MAX_HISTORY_CHARS = 4000  # Approximate token limit (adjust as needed) ~1000 tokens

#Markdown support
# ONE-LINE FILTER ⤵
app.jinja_env.filters["md"] = lambda text: Markup(
    markdown.markdown(text, extensions=["fenced_code"])
)

# --- Global Variables for Persistent Connection ---
global_client = None
background_thread = None
event_loop = None
client_lock = threading.Lock()

# --- MCP Client Class ---
class MCPWebClient:
    """MCP client for web interface."""
    
    def __init__(self):
        self.process = None
        self.request_id = 0
        self.connected = False
    
    async def connect_old(self, command: list):
        """Connect to MCP server using stdio transport."""
        try:
            logging.info("Starting MCP server process...")
            self.process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Initialize the connection
            await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "watsonx-web-client",
                    "version": "1.0.0"
                }
            })
            
            # Send initialized notification
            await self._send_notification("notifications/initialized")
            self.connected = True
            logging.info("MCP server connection established successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to connect to server: {e}")
            self.connected = False
            return False
    

    async def connect(self, command: list):
        """Connect to MCP server using stdio transport."""
        try:
            logging.info("Starting MCP server process...")
            self.process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # 🤖 Mark “connected” now so _send_request can fire the first init call:
            self.connected = True

            # Initialize the connection
            await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "watsonx-web-client",
                    "version": "1.0.0"
                }
            })

            # Send initialized notification
            await self._send_notification("notifications/initialized")

            logging.info("MCP server connection established successfully")
            return True

        except Exception as e:
            logging.error(f"Failed to connect to server: {e}")
            # rollback if anything went wrong
            self.connected = False
            return False



    async def _send_request(self, method: str, params: dict = None) -> dict:
        """Send a JSON-RPC request to the server."""
        if not self.connected or not self.process:
            raise Exception("Not connected to MCP server")
            
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }
        
        message = json.dumps(request) + "\n"
        self.process.stdin.write(message.encode())
        await self.process.stdin.drain()
        
        # Read response
        response_line = await self.process.stdout.readline()
        if not response_line:
            raise Exception("No response from server")
        
        response = json.loads(response_line.decode().strip())
        return response
    
    async def _send_notification(self, method: str, params: dict = None):
        """Send a JSON-RPC notification to the server."""
        if not self.connected or not self.process:
            raise Exception("Not connected to MCP server")
            
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        
        message = json.dumps(notification) + "\n"
        self.process.stdin.write(message.encode())
        await self.process.stdin.drain()
    
    async def call_tool(self, name: str, arguments: dict = None) -> dict:
        """Call a tool on the server."""
        return await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments or {}
        })
    
    async def chat_with_watsonx(self, message: str, temperature: float = 0.7, max_tokens: int = 200):
        """Send a chat message to watsonx."""
        try:
            response = await self.call_tool("chat_with_watsonx", {
                "query": message,
                "temperature": temperature,
                "max_tokens": max_tokens
            })
            
            if "result" in response and "content" in response["result"]:
                return response["result"]["content"][0]["text"], None
            elif "error" in response:
                return None, f"Error: {response['error'].get('message', 'Unknown error')}"
            else:
                return None, "Unexpected response format"
                
        except Exception as e:
            return None, f"Connection error: {e}"
    
    async def analyze_symptoms(self, symptoms: str, age: int = None, gender: str = None):
        """Analyze medical symptoms."""
        try:
            args = {"symptoms": symptoms}
            if age:
                args["patient_age"] = age
            if gender:
                args["patient_gender"] = gender
            
            response = await self.call_tool("analyze_medical_symptoms", args)
            
            if "result" in response and "content" in response["result"]:
                return response["result"]["content"][0]["text"], None
            elif "error" in response:
                return None, f"Error: {response['error'].get('message', 'Unknown error')}"
            else:
                return None, "Unexpected response format"
                
        except Exception as e:
            return None, f"Connection error: {e}"
    
    async def clear_history(self):
        """Clear conversation history."""
        try:
            response = await self.call_tool("clear_conversation_history")
            if "result" in response and "content" in response["result"]:
                return response["result"]["content"][0]["text"], None
            else:
                return "Conversation history cleared", None
        except Exception as e:
            return None, f"Error clearing history: {e}"
    
    async def get_summary(self):
        """Get conversation summary."""
        try:
            response = await self.call_tool("get_conversation_summary")
            if "result" in response and "content" in response["result"]:
                return response["result"]["content"][0]["text"], None
            else:
                return "No conversation to summarize", None
        except Exception as e:
            return None, f"Error getting summary: {e}"
    
    async def read_resource(self, uri: str):
        """Read a resource from the server."""
        try:
            response = await self._send_request("resources/read", {"uri": uri})
            if "result" in response:
                return response["result"], None
            else:
                return None, "Resource not found"
        except Exception as e:
            return None, f"Error reading resource: {e}"
    
    async def get_prompt(self, name: str, arguments: dict = None):
        """Get a prompt from the server."""
        try:
            response = await self._send_request("prompts/get", {
                "name": name,
                "arguments": arguments or {}
            })
            if "result" in response:
                return response["result"], None
            else:
                return None, "Prompt not found"
        except Exception as e:
            return None, f"Error getting prompt: {e}"
    
    async def close(self):
        """Close the connection to the server."""
        if self.process:
            try:
                self.connected = False
                self.process.stdin.close()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
                logging.info("MCP server connection closed gracefully")
            except asyncio.TimeoutError:
                self.process.terminate()
                await self.process.wait()
                logging.info("MCP server process terminated")

# --- Background Thread Functions ---

def run_event_loop():
    """Run the asyncio event loop in a background thread."""
    global event_loop
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    event_loop.run_forever()

async def initialize_mcp_client():
    """Initialize the global MCP client."""
    global global_client
    global_client = MCPWebClient()
    
    # Try to connect with retries
    max_retries = 3
    for attempt in range(max_retries):
        try:
            connected = await global_client.connect([sys.executable, "server.py"])
            if connected:
                logging.info("Global MCP client initialized successfully")
                return True
            else:
                logging.warning(f"Connection attempt {attempt + 1} failed")
        except Exception as e:
            logging.error(f"Connection attempt {attempt + 1} failed: {e}")
        
        if attempt < max_retries - 1:
            await asyncio.sleep(2)  # Wait before retry
    
    logging.error("Failed to initialize MCP client after all retries")
    return False

def start_background_services():
    """Start the background thread and initialize MCP client."""
    global background_thread, event_loop
    
    # Start the background event loop thread
    background_thread = threading.Thread(target=run_event_loop, daemon=True)
    background_thread.start()
    
    # Wait a moment for the event loop to start
    import time
    time.sleep(0.5)
    
    # Initialize the MCP client
    future = asyncio.run_coroutine_threadsafe(initialize_mcp_client(), event_loop)
    try:
        success = future.result(timeout=30)  # 30 second timeout
        if not success:
            logging.error("Failed to start background services")
    except Exception as e:
        logging.error(f"Error starting background services: {e}")

def stop_background_services():
    """Stop the background services and close MCP client."""
    global global_client, event_loop, background_thread
    
    if global_client and event_loop:
        try:
            future = asyncio.run_coroutine_threadsafe(global_client.close(), event_loop)
            future.result(timeout=10)
        except Exception as e:
            logging.error(f"Error closing MCP client: {e}")
    
    if event_loop:
        event_loop.call_soon_threadsafe(event_loop.stop)
    
    if background_thread and background_thread.is_alive():
        background_thread.join(timeout=5)
    
    logging.info("Background services stopped")

# --- Helper Functions ---

def call_mcp_action(action: str, **kwargs):
    """
    Thread-safe wrapper to call MCP actions using the persistent connection.
    """
    global global_client, event_loop, client_lock
    
    if not global_client or not event_loop:
        return None, "MCP client not initialized"
    
    with client_lock:  # Ensure thread safety
        try:
            if action == "chat":
                coro = global_client.chat_with_watsonx(
                    kwargs.get("message", ""),
                    kwargs.get("temperature", 0.7),
                    kwargs.get("max_tokens", 200)
                )
            elif action == "analyze_symptoms":
                coro = global_client.analyze_symptoms(
                    kwargs.get("symptoms", ""),
                    kwargs.get("age"),
                    kwargs.get("gender")
                )
            elif action == "clear_history":
                coro = global_client.clear_history()
            elif action == "get_summary":
                coro = global_client.get_summary()
            elif action == "get_greeting":
                name = kwargs.get("name", "Patient")
                coro = global_client.read_resource(f"greeting://patient/{name}")
            elif action == "get_server_info":
                coro = global_client.read_resource("info://server")
            else:
                return None, f"Unknown action: {action}"
            
            # Execute the coroutine in the background thread
            future = asyncio.run_coroutine_threadsafe(coro, event_loop)
            response_text, error_message = future.result(timeout=30)  # 30 second timeout
            
            # Process special response formats
            if action in ["get_greeting", "get_server_info"] and response_text and isinstance(response_text, dict):
                response_text = response_text.get("contents", [{}])[0].get("text", "Information not available")
            
            return response_text, error_message
            
        except Exception as e:
            logging.error(f"Error during MCP call: {e}", exc_info=True)
            return None, f"Internal error: {e}"

def parse_message_for_action(message: str) -> tuple[str, dict]:
    """
    Parse user message to determine action and extract parameters.
    Returns (action, kwargs)
    """
    message_lower = message.lower().strip()
    
    # Check for symptom analysis
    if message_lower.startswith('symptoms:') or message_lower.startswith('analyze:'):
        symptoms = message[message.find(':') + 1:].strip()
        return "analyze_symptoms", {"symptoms": symptoms}
    
    # Check for medical keywords
    medical_keywords = ['pain', 'fever', 'headache', 'nausea', 'cough', 'symptoms', 'hurt', 'ache', 'sick', 'illness']
    if any(keyword in message_lower for keyword in medical_keywords):
        # If it seems medical but not explicitly asking for analysis, treat as symptom analysis
        if any(phrase in message_lower for phrase in ['i have', 'experiencing', 'feeling', 'symptoms']):
            return "analyze_symptoms", {"symptoms": message}
    
    # Default to regular chat
    return "chat", {"message": message}

def trim_history(history: list, max_chars: int) -> list:
    """Removes oldest messages if total character count exceeds max_chars."""
    current_chars = sum(len(msg.get('content', '')) for msg in history)
    
    while current_chars > max_chars and len(history) > 2:
        removed_message = history.pop(0)
        current_chars -= len(removed_message.get('content', ''))
        logging.info(f"History trimmed. Current chars: {current_chars}")
    
    return history

# --- Flask Routes ---

@app.route('/')
def index():
    """Displays the chat interface."""
    if 'history' not in session:
        session['history'] = []
        # Add welcome message
        welcome_msg = "🤖 Welcome to Watsonx Medical Assistant! I can help you with:\n\n" \
                     "• General health questions\n" \
                     "• Medical symptom analysis\n" \
                     "• Health information\n\n" \
                     "Try typing 'symptoms: [your symptoms]' for medical analysis, or just ask me anything!"
        session['history'].append({"role": "assistant", "content": welcome_msg})
    
    return render_template('chat.html', history=session['history'])

@app.route('/chat', methods=['POST'])
def chat():
    """Handles user messages and gets bot responses."""
    user_message = request.form.get('message')

    if not user_message:
        return redirect(url_for('index'))

    # Ensure history exists in session
    if 'history' not in session:
        session['history'] = []

    # Add user message to history
    session['history'].append({"role": "user", "content": user_message})

    # Parse message to determine action
    action, kwargs = parse_message_for_action(user_message)
    
    # Get response from MCP backend using persistent connection
    bot_response, error = call_mcp_action(action, **kwargs)

    if error:
        session['history'].append({"role": "error", "content": error})

    elif bot_response:
        # Add appropriate prefix based on action
        if action == "analyze_symptoms":
            bot_response = f"🏥 **Medical Analysis:**\n\n{bot_response}\n\n⚠️ *This is for informational purposes only. Please consult a healthcare professional for proper medical advice.*"
        session['history'].append({"role": "assistant", "content": bot_response})
    else:
        session['history'].append({"role": "error", "content": "No response received from the backend."})

    # Trim history after adding new messages
    session['history'] = trim_history(session['history'], MAX_HISTORY_CHARS)
    session.modified = True

    return redirect(url_for('index'))


@app.route('/clear')
def clear_chat():
    """Clears the chat history from the session and server."""
    # Clear server-side history
    _, error = call_mcp_action("clear_history")
    
    # Clear session history
    session.pop('history', None)
    
    logging.info("Chat history cleared.")
    return redirect(url_for('index'))


@app.route('/summary')
def get_summary():
    """Gets conversation summary from the server."""
    if 'history' not in session:
        session['history'] = []
    
    summary, error = call_mcp_action("get_summary")
    
    if error:
        session['history'].append({"role": "error", "content": f"Summary error: {error}"})
    elif summary:
        session['history'].append({"role": "assistant", "content": f"📋 **Conversation Summary:**\n\n{summary}"})
    else:
        session['history'].append({"role": "assistant", "content": "📋 No conversation to summarize yet."})
    
    session.modified = True
    return redirect(url_for('index'))


@app.route('/analyze_symptoms', methods=['POST'])
def analyze_symptoms():
    """Dedicated endpoint for symptom analysis with structured input."""
    symptoms = request.form.get('symptoms', '').strip()
    age = request.form.get('age', '').strip()
    gender = request.form.get('gender', '').strip()
    
    if not symptoms:
        return redirect(url_for('index'))
    
    # Ensure history exists in session
    if 'history' not in session:
        session['history'] = []
    
    # Format the user input message
    user_input = f"Symptoms: {symptoms}"
    if age:
        try:
            age_int = int(age)
            user_input += f", Age: {age_int}"
        except ValueError:
            age = None
    if gender:
        user_input += f", Gender: {gender}"
    
    # Add user message to history
    session['history'].append({"role": "user", "content": user_input})
    
    # Prepare arguments for symptom analysis
    kwargs = {"symptoms": symptoms}
    if age:
        try:
            kwargs["age"] = int(age)
        except ValueError:
            pass
    if gender:
        kwargs["gender"] = gender
    
    # Get response from MCP backend using persistent connection
    bot_response, error = call_mcp_action("analyze_symptoms", **kwargs)
    
    if error:
        session['history'].append({"role": "error", "content": error})
    elif bot_response:
        formatted_response = f"🏥 **Medical Analysis:**\n\n{bot_response}\n\n⚠️ *This is for informational purposes only. Please consult a healthcare professional for proper medical advice.*"
        session['history'].append({"role": "assistant", "content": formatted_response})
    else:
        session['history'].append({"role": "error", "content": "No response received from the medical analysis."})
    
    # Trim history after adding new messages
    session['history'] = trim_history(session['history'], MAX_HISTORY_CHARS)
    session.modified = True
    
    return redirect(url_for('index'))


@app.route('/server_info')
def server_info():
    """Gets server information."""
    if 'history' not in session:
        session['history'] = []
    
    info, error = call_mcp_action("get_server_info")
    
    if error:
        session['history'].append({"role": "error", "content": f"Server info error: {error}"})
    elif info:
        session['history'].append({"role": "assistant", "content": f"ℹ️ **Server Information:**\n\n{info}"})
    else:
        session['history'].append({"role": "assistant", "content": "ℹ️ Server information not available."})
    
    session.modified = True
    return redirect(url_for('index'))


@app.route('/greeting/<name>')
def get_greeting(name):
    """Gets a personalized patient greeting."""
    if 'history' not in session:
        session['history'] = []
    
    greeting, error = call_mcp_action("get_greeting", name=name)
    
    if error:
        session['history'].append({"role": "error", "content": f"Greeting error: {error}"})
    elif greeting:
        session['history'].append({"role": "assistant", "content": f"👋 {greeting}"})
    else:
        session['history'].append({"role": "assistant", "content": f"👋 Hello {name}! Welcome to the Medical Assistant."})
    
    session.modified = True
    return redirect(url_for('index'))


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """API endpoint for chat (JSON response)."""
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "No message provided"}), 400
    
    user_message = data['message']
    action, kwargs = parse_message_for_action(user_message)
    
    bot_response, error = call_mcp_action(action, **kwargs)
    
    if error:
        return jsonify({"error": error}), 500
    
    return jsonify({
        "response": bot_response,
        "action": action,
        "success": True
    })


@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """API endpoint for symptom analysis (JSON response)."""
    data = request.get_json()
    if not data or 'symptoms' not in data:
        return jsonify({"error": "No symptoms provided"}), 400
    
    kwargs = {"symptoms": data['symptoms']}
    if 'age' in data:
        kwargs['age'] = data['age']
    if 'gender' in data:
        kwargs['gender'] = data['gender']
    
    bot_response, error = call_mcp_action("analyze_symptoms", **kwargs)
    
    if error:
        return jsonify({"error": error}), 500
    
    return jsonify({
        "analysis": bot_response,
        "success": True
    })


@app.route('/help')
def help_page():
    """Shows help information."""
    if 'history' not in session:
        session['history'] = []
    
    help_text = """
🤖 **Watsonx Medical Assistant Help**

**Available Features:**
• **General Chat**: Ask me any health-related questions
• **Symptom Analysis**: Get preliminary medical assessments
• **Health Information**: Learn about medical conditions and treatments

**How to Use:**
• **Regular Chat**: Just type your question normally
• **Symptom Analysis**: Type "symptoms: [your symptoms]" or use the analyze form
• **Clear History**: Click "Clear Chat" to start fresh
• **Get Summary**: Click "Summary" to get a conversation overview

**Special Commands:**
• Type "symptoms: headache and fever" for quick symptom analysis
• Medical keywords (pain, fever, etc.) automatically trigger symptom analysis
• Ask about specific conditions, treatments, or health topics

**Examples:**
• "What causes high blood pressure?"
• "symptoms: chest pain and shortness of breath"
• "Tell me about diabetes management"
• "I have a headache and nausea"

**Important Notes:**
⚠️ This assistant provides general health information only
⚠️ Always consult healthcare professionals for medical advice
⚠️ In emergencies, contact emergency services immediately

**Navigation:**
• Use the links at the top to access different features
• Your conversation history is maintained during your session
• Clear chat to start a new conversation
    """
    
    session['history'].append({"role": "assistant", "content": help_text})
    session.modified = True
    
    return redirect(url_for('index'))


@app.route('/health')
def health_check():
    """Health check endpoint to verify MCP connection status."""
    global global_client
    
    if global_client and global_client.connected:
        return jsonify({
            "status": "healthy",
            "mcp_connected": True,
            "message": "MCP server connection is active"
        }), 200
    else:
        return jsonify({
            "status": "unhealthy",
            "mcp_connected": False,
            "message": "MCP server connection is not available"
        }), 503


@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Page not found"), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Internal server error"), 500


# --- Additional Template Context ---
@app.context_processor
def inject_template_vars():
    """Inject variables available to all templates."""
    return {
        'app_name': 'Watsonx Medical Assistant',
        'version': '1.0.0'
    }


# --- Application Lifecycle Management ---

#@app.before_first_request
#def initialize_app():
#    """Initialize the application on first request."""
#    logging.info("Initializing application...")
#    start_background_services()


# Register cleanup function to run when the application shuts down
atexit.register(stop_background_services)


# --- Run the App ---
if __name__ == '__main__':

    
    # Ensure server.py exists
    if not os.path.exists('server.py'):
        print("ERROR: server.py not found in the current directory!")
        print("Please make sure server.py is in the same directory as frontend.py")
        sys.exit(1)
    
    print("🚀 Starting Watsonx Medical Assistant Web Interface...")
    print("📋 Available features:")
    print("   • General health chat")
    print("   • Medical symptom analysis") 
    print("   • Conversation management")
    print("   • Health information lookup")
    print("   • Persistent MCP server connection")
    print("\n🌐 Access the application at: http://localhost:5001")
    print("📖 Visit /help for usage instructions")
    print("🔍 Visit /health for connection status")
    
    # Start background services before running the app
    start_background_services()
    
    try:
        # Consider using waitress or gunicorn for production instead of Flask's dev server
        app.run(debug=True, host='0.0.0.0', port=5001, threaded=True)
    finally:
        # Ensure cleanup happens even if the app crashes
        stop_background_services()        