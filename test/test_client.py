# test/test_client.py

import asyncio
import json
import sys
import os
from typing import Dict, Any


class MCPClient:
    """Simple MCP client for connecting to MCP servers via stdio transport."""

    def __init__(self):
        self.process = None
        self.request_id = 0

    async def connect(self, command: list):
        """Connect to MCP server using stdio transport."""
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
                "clientInfo": {"name": "simple-mcp-client", "version": "1.0.0"},
            },
        )

        # Send initialized notification
        await self._send_notification("notifications/initialized")

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

    async def list_tools(self) -> Dict[str, Any]:
        """List available tools from the server."""
        return await self._send_request("tools/list")

    async def call_tool(
        self, name: str, arguments: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Call a tool on the server."""
        return await self._send_request(
            "tools/call", {"name": name, "arguments": arguments or {}}
        )

    async def list_resources(self) -> Dict[str, Any]:
        """List available resources from the server."""
        return await self._send_request("resources/list")

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource from the server."""
        return await self._send_request("resources/read", {"uri": uri})

    async def list_prompts(self) -> Dict[str, Any]:
        """List available prompts from the server."""
        return await self._send_request("prompts/list")

    async def get_prompt(
        self, name: str, arguments: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Get a prompt from the server."""
        return await self._send_request(
            "prompts/get", {"name": name, "arguments": arguments or {}}
        )

    async def close(self):
        """Close the connection to the server."""
        if self.process:
            self.process.stdin.close()
            await self.process.wait()


async def main():
    """Example usage of the MCP client."""
    client = MCPClient()

    try:
        # Determine the path to server.py in the project root
        script_dir = os.path.dirname(__file__)  # test/
        root_dir = os.path.abspath(os.path.join(script_dir, os.pardir))
        server_path = os.path.join(root_dir, "server.py")

        # Use the same Python interpreter
        await client.connect([sys.executable, server_path])

        print("Connected to MCP server!")

        # List available tools
        print("\n=== Available Tools ===")
        tools_response = await client.list_tools()
        if "result" in tools_response and "tools" in tools_response["result"]:
            for tool in tools_response["result"]["tools"]:
                print(f"- {tool['name']}: {tool.get('description', 'No description')}")

        # List available resources
        print("\n=== Available Resources ===")
        resources_response = await client.list_resources()
        if (
            "result" in resources_response
            and "resources" in resources_response["result"]
        ):
            for resource in resources_response["result"]["resources"]:
                print(
                    f"- {resource['uri']}: {resource.get('description', 'No description')}"
                )

        # List available prompts
        print("\n=== Available Prompts ===")
        prompts_response = await client.list_prompts()
        if "result" in prompts_response and "prompts" in prompts_response["result"]:
            for prompt in prompts_response["result"]["prompts"]:
                print(
                    f"- {prompt['name']}: {prompt.get('description', 'No description')}"
                )

        # Example: Chat with watsonx
        print("\n=== Testing chat_with_watsonx tool ===")
        chat_response = await client.call_tool(
            "chat_with_watsonx",
            {
                "query": "Hello! How are you today?",
                "max_tokens": 100,
                "temperature": 0.7,
            },
        )

        if "result" in chat_response:
            print("Chat response:", chat_response["result"])
        else:
            print("Error in chat response:", chat_response)

        # Example: Get server info resource
        print("\n=== Testing server info resource ===")
        server_info = await client.read_resource("info://server")
        if "result" in server_info:
            print("Server info:", server_info["result"])

        # Example: Get a patient greeting
        print("\n=== Testing patient greeting resource ===")
        greeting = await client.read_resource("greeting://patient/John")
        if "result" in greeting:
            print("Patient greeting:", greeting["result"])

        # Example: Get medical consultation prompt
        print("\n=== Testing medical consultation prompt ===")
        prompt_response = await client.get_prompt(
            "medical_consultation_prompt",
            {
                "symptoms": "headache and fever",
                "duration": "2 days",
                "severity": "moderate",
            },
        )
        if "result" in prompt_response:
            print("Medical consultation prompt:", prompt_response["result"])

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
