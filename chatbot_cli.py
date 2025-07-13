# chatbot-cli.py

import asyncio
import json
import sys
from typing import Dict, Any


class MCPChatbot:
    """Interactive chatbot client for MCP server."""

    def __init__(self):
        self.process = None
        self.request_id = 0
        self.conversation_active = True

    async def connect(self, command: list):
        """Connect to MCP server using stdio transport."""
        try:
            self.process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Initialize the connection
            await self._send_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                    "clientInfo": {"name": "watsonx-chatbot", "version": "1.0.0"},
                },
            )

            # Send initialized notification
            await self._send_notification("notifications/initialized")
            return True

        except Exception as e:
            print(f"❌ Failed to connect to server: {e}")
            return False

    async def _send_request(
        self, method: str, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Send a JSON-RPC request to the server."""
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {},
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

    async def _send_notification(self, method: str, params: Dict[str, Any] = None):
        """Send a JSON-RPC notification to the server."""
        notification = {"jsonrpc": "2.0", "method": method, "params": params or {}}

        message = json.dumps(notification) + "\n"
        self.process.stdin.write(message.encode())
        await self.process.stdin.drain()

    async def call_tool(
        self, name: str, arguments: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Call a tool on the server."""
        return await self._send_request(
            "tools/call", {"name": name, "arguments": arguments or {}}
        )

    async def chat_with_watsonx(
        self, message: str, temperature: float = 0.7, max_tokens: int = 200
    ):
        """Send a chat message to watsonx."""
        try:
            response = await self.call_tool(
                "chat_with_watsonx",
                {
                    "query": message,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )

            if "result" in response and "content" in response["result"]:
                return response["result"]["content"][0]["text"]
            elif "error" in response:
                return f"❌ Error: {response['error'].get('message', 'Unknown error')}"
            else:
                return "❌ Unexpected response format"

        except Exception as e:
            return f"❌ Connection error: {e}"

    async def analyze_symptoms(
        self, symptoms: str, age: int = None, gender: str = None
    ):
        """Analyze medical symptoms."""
        try:
            args = {"symptoms": symptoms}
            if age:
                args["patient_age"] = age
            if gender:
                args["patient_gender"] = gender

            response = await self.call_tool("analyze_medical_symptoms", args)

            if "result" in response and "content" in response["result"]:
                return response["result"]["content"][0]["text"]
            elif "error" in response:
                return f"❌ Error: {response['error'].get('message', 'Unknown error')}"
            else:
                return "❌ Unexpected response format"

        except Exception as e:
            return f"❌ Connection error: {e}"

    async def clear_history(self):
        """Clear conversation history."""
        try:
            response = await self.call_tool("clear_conversation_history")
            if "result" in response and "content" in response["result"]:
                return response["result"]["content"][0]["text"]
            else:
                return "✅ Conversation history cleared"
        except Exception as e:
            return f"❌ Error clearing history: {e}"

    async def get_summary(self):
        """Get conversation summary."""
        try:
            response = await self.call_tool("get_conversation_summary")
            if "result" in response and "content" in response["result"]:
                return response["result"]["content"][0]["text"]
            else:
                return "No conversation to summarize"
        except Exception as e:
            return f"❌ Error getting summary: {e}"

    def print_help(self):
        """Print available commands."""
        help_text = """
🤖 Watsonx Medical Assistant Chatbot

Available commands:
  /help          - Show this help message
  /symptoms      - Analyze medical symptoms (interactive mode)
  /clear         - Clear conversation history
  /summary       - Get conversation summary
  /quit or /exit - Exit the chatbot

For medical symptom analysis, you can also type:
  symptoms: <your symptoms>

Otherwise, just type your message to chat with the AI assistant.

Examples:
  - "Hello, how are you?"
  - "symptoms: I have a headache and fever"
  - "/symptoms" (for interactive symptom analysis)
        """
        print(help_text)

    async def interactive_symptom_analysis(self):
        """Interactive symptom analysis."""
        print("\n🏥 Medical Symptom Analysis")
        print("Please provide the following information:")

        symptoms = input("Symptoms: ").strip()
        if not symptoms:
            print("❌ No symptoms provided.")
            return

        age_input = input("Age (optional, press Enter to skip): ").strip()
        age = None
        if age_input:
            try:
                age = int(age_input)
            except ValueError:
                print("⚠️  Invalid age, skipping...")

        gender = input("Gender (optional, press Enter to skip): ").strip()
        if not gender:
            gender = None

        print("\n🔍 Analyzing symptoms...")
        result = await self.analyze_symptoms(symptoms, age, gender)
        print(f"\n🏥 Medical Analysis:\n{result}")

    async def process_message(self, message: str):
        """Process user message and return response."""
        message = message.strip()

        if not message:
            return

        # Handle commands
        if message.startswith("/"):
            command = message.lower()

            if command in ["/quit", "/exit"]:
                self.conversation_active = False
                print("👋 Goodbye! Take care of your health!")
                return

            elif command == "/help":
                self.print_help()
                return

            elif command == "/clear":
                result = await self.clear_history()
                print(f"🧹 {result}")
                return

            elif command == "/summary":
                print("📋 Getting conversation summary...")
                result = await self.get_summary()
                print(f"📋 Summary:\n{result}")
                return

            elif command == "/symptoms":
                await self.interactive_symptom_analysis()
                return

            else:
                print(f"❌ Unknown command: {command}")
                print("Type /help for available commands.")
                return

        # Handle symptom analysis shortcut
        if message.lower().startswith("symptoms:"):
            symptoms = message[9:].strip()
            if symptoms:
                print("🔍 Analyzing symptoms...")
                result = await self.analyze_symptoms(symptoms)
                print(f"\n🏥 Medical Analysis:\n{result}")
            else:
                print("❌ Please provide symptoms after 'symptoms:'")
            return

        # Regular chat
        print("🤖 Thinking...")
        response = await self.chat_with_watsonx(message)
        print(f"🤖 Assistant: {response}")

    async def run_chat_loop(self):
        """Main chat loop."""
        print("🤖 Watsonx Medical Assistant Chatbot")
        print("Type /help for commands or just start chatting!")
        print("=" * 50)

        while self.conversation_active:
            try:
                # Get user input
                user_input = input("\n💬 You: ").strip()

                if not user_input:
                    continue

                await self.process_message(user_input)

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye! Take care!")
                break
            except EOFError:
                print("\n\n👋 Goodbye! Take care!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    async def close(self):
        """Close the connection to the server."""
        if self.process:
            try:
                self.process.stdin.close()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.terminate()
                await self.process.wait()


async def main():
    """Main function to run the chatbot."""
    chatbot = MCPChatbot()

    try:
        print("🔌 Connecting to Watsonx Medical Assistant server...")

        # Connect to your server (adjust the command as needed)
        connected = await chatbot.connect(["python", "server.py"])

        if not connected:
            print(
                "❌ Failed to connect to server. Make sure server.py is in the same directory."
            )
            return

        print("✅ Connected successfully!")

        # Run the chat loop
        await chatbot.run_chat_loop()

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await chatbot.close()


if __name__ == "__main__":
    # Handle Windows event loop policy
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())
