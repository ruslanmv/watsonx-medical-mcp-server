"""
backend.py – persistent MCP client with safe, serialised I/O
============================================================

* One MCP subprocess is reused for the whole web-app session.
* All JSON-RPC traffic happens on a dedicated background event-loop thread.
* Every stdin/stdout operation is protected by an `asyncio.Lock`, so
  concurrent requests can never race on the pipes.

Set BACKEND_LOG_LEVEL=DEBUG for verbose traces.
"""

from __future__ import annotations

import asyncio
import atexit
import json
import logging
import os
import sys
import threading
from typing import Any, Dict, Optional, Tuple

# ──────────────────────────────── logging ────────────────────────────────
_LOG_LEVEL = os.getenv("BACKEND_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _LOG_LEVEL, logging.INFO),
    format="%(asctime)s [Backend] %(levelname)s: %(message)s",
)
logger = logging.getLogger("backend")


# ─────────────────────────── MCP JSON-RPC client ──────────────────────────
class MCPWebClient:
    def __init__(self) -> None:
        self.process: Optional[asyncio.subprocess.Process] = None
        self.request_id: int = 0
        self._io_lock: Optional[asyncio.Lock] = None  # created lazily

    # — connection —
    async def connect(self, command: list[str]) -> bool:
        if self.process and self.process.returncode is None:
            logger.debug("MCP already running – skip spawn.")
            return True

        logger.info("Spawning MCP server: %s", " ".join(command))
        self.process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._io_lock = asyncio.Lock()

        try:
            await self._send_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "watsonx-web-client", "version": "1.0.0"},
                },
            )
            await self._send_notification("notifications/initialized")
            logger.info("MCP handshake completed.")
            return True
        except Exception:  # noqa: BLE001
            logger.exception("Handshake failed.")
            return False

    async def close(self) -> None:
        if not self.process:
            return
        logger.info("Closing MCP connection …")
        try:
            if self.process.stdin and not self.process.stdin.is_closing():
                self.process.stdin.close()
            await asyncio.wait_for(self.process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("MCP server unresponsive – forcing terminate.")
            self.process.terminate()
            await self.process.wait()

    # — low-level JSON-RPC helpers —
    async def _send_request(
        self, method: str, params: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        if self._io_lock is None:  # pragma: no cover
            self._io_lock = asyncio.Lock()

        async with self._io_lock:
            self.request_id += 1
            req = {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "method": method,
                "params": params or {},
            }

            assert (
                self.process and self.process.stdin and self.process.stdout
            ), "MCP process not connected"

            logger.debug("→ %s %s", method, params)
            self.process.stdin.write((json.dumps(req) + "\n").encode())
            await self.process.stdin.drain()

            line = await self.process.stdout.readline()
            if not line:
                raise RuntimeError("No response from MCP server")

            resp = json.loads(line.decode().strip())
            logger.debug("← %s", resp)
            return resp

    async def _send_notification(
        self, method: str, params: Dict[str, Any] | None = None
    ) -> None:
        if self._io_lock is None:
            self._io_lock = asyncio.Lock()

        async with self._io_lock:
            note = {"jsonrpc": "2.0", "method": method, "params": params or {}}
            assert self.process and self.process.stdin
            logger.debug("→ (notify) %s %s", method, params)
            self.process.stdin.write((json.dumps(note) + "\n").encode())
            await self.process.stdin.drain()

    # — high-level wrappers —
    async def call_tool(
        self, name: str, arguments: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        return await self._send_request(
            "tools/call", {"name": name, "arguments": arguments or {}}
        )

    async def chat_with_watsonx(
        self, message: str, temperature: float = 0.7, max_tokens: int = 200
    ) -> Tuple[Optional[str], Optional[str]]:
        try:
            resp = await self.call_tool(
                "chat_with_watsonx",
                {
                    "query": message,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            if "result" in resp and "content" in resp["result"]:
                return resp["result"]["content"][0]["text"], None
            if "error" in resp:
                return None, resp["error"].get("message", "Unknown error")
            return None, "Unexpected response format"
        except Exception as exc:  # noqa: BLE001
            return None, f"Connection error: {exc}"

    async def analyze_symptoms(
        self, symptoms: str, age: int | None = None, gender: str | None = None
    ) -> Tuple[Optional[str], Optional[str]]:
        args: Dict[str, Any] = {"symptoms": symptoms}
        if age is not None:
            args["patient_age"] = age
        if gender:
            args["patient_gender"] = gender
        try:
            resp = await self.call_tool("analyze_medical_symptoms", args)
            if "result" in resp and "content" in resp["result"]:
                return resp["result"]["content"][0]["text"], None
            if "error" in resp:
                return None, resp["error"].get("message", "Unknown error")
            return None, "Unexpected response format"
        except Exception as exc:  # noqa: BLE001
            return None, f"Connection error: {exc}"

    async def clear_history(self) -> Tuple[Optional[str], Optional[str]]:
        try:
            resp = await self.call_tool("clear_conversation_history")
            if "result" in resp and "content" in resp["result"]:
                return resp["result"]["content"][0]["text"], None
            return "Conversation history cleared.", None
        except Exception as exc:  # noqa: BLE001
            return None, f"Error clearing history: {exc}"

    async def get_summary(self) -> Tuple[Optional[str], Optional[str]]:
        try:
            resp = await self.call_tool("get_conversation_summary")
            if "result" in resp and "content" in resp["result"]:
                return resp["result"]["content"][0]["text"], None
            return "No conversation to summarise.", None
        except Exception as exc:  # noqa: BLE001
            return None, f"Error getting summary: {exc}"

    async def read_resource(
        self, uri: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        try:
            resp = await self._send_request("resources/read", {"uri": uri})
            if "result" in resp:
                return resp["result"], None
            return None, "Resource not found"
        except Exception as exc:  # noqa: BLE001
            return None, f"Error reading resource: {exc}"


# ───────────────────── background event-loop (daemon thread) ───────────────
_backend_loop = asyncio.new_event_loop()


def _loop_runner(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    loop.run_forever()


threading.Thread(target=_loop_runner, args=(_backend_loop,), daemon=True).start()

_client = MCPWebClient()
_connect_lock: Optional[asyncio.Lock] = None  # created lazily inside loop


async def _ensure_connected() -> None:
    """Serialise connection attempts with a loop-local lock."""
    global _connect_lock
    if _connect_lock is None:
        _connect_lock = asyncio.Lock()  # bound to _backend_loop
    async with _connect_lock:
        if _client.process and _client.process.returncode is None:
            return
        connected = await _client.connect([sys.executable, "server.py"])
        if not connected:
            raise RuntimeError("Unable to establish MCP connection.")


# ───────────────────── internal dispatcher (runs on loop) ──────────────────
async def _async_dispatch(action: str, **kwargs) -> Tuple[Optional[str], Optional[str]]:
    await _ensure_connected()

    if action == "chat":
        return await _client.chat_with_watsonx(
            kwargs.get("message", ""),
            kwargs.get("temperature", 0.7),
            kwargs.get("max_tokens", 200),
        )

    if action == "analyze_symptoms":
        return await _client.analyze_symptoms(
            kwargs.get("symptoms", ""),
            kwargs.get("age"),
            kwargs.get("gender"),
        )

    if action == "clear_history":
        return await _client.clear_history()

    if action == "get_summary":
        return await _client.get_summary()

    if action == "get_greeting":
        name = kwargs.get("name", "Patient")
        resource, err = await _client.read_resource(f"greeting://patient/{name}")
        if err:
            return None, err
        if isinstance(resource, dict):
            text = resource.get("contents", [{}])[0].get("text", "Hello!")
            return text, None
        return None, "Unknown greeting format"

    if action == "get_server_info":
        resource, err = await _client.read_resource("info://server")
        if err:
            return None, err
        if isinstance(resource, dict):
            text = resource.get("contents", [{}])[0].get("text", "No server info")
            return text, None
        return None, "Unknown info format"

    return None, f"Unknown action: {action}"


# ───────────────────── synchronous facade for Flask ────────────────────────
def get_mcp_response(action: str, **kwargs) -> Tuple[Optional[str], Optional[str]]:
    """
    Called by Flask (sync context).  Schedules a coroutine on the background
    event-loop and blocks until the result is ready.
    """
    try:
        fut = asyncio.run_coroutine_threadsafe(
            _async_dispatch(action, **kwargs), _backend_loop
        )
        return fut.result()  # blocks caller thread
    except Exception as exc:  # noqa: BLE001
        logger.exception("Backend action '%s' failed.", action)
        return None, f"Internal backend error: {exc}"


# ───────────────────── chat message → backend action helper ────────────────
_MEDICAL_KEYWORDS = {
    "pain",
    "fever",
    "headache",
    "nausea",
    "cough",
    "symptoms",
    "hurt",
    "ache",
    "sick",
    "illness",
}


def parse_message_for_action(message: str) -> Tuple[str, Dict[str, Any]]:
    txt = message.lower().strip()

    if txt.startswith(("symptoms:", "analyze:")):
        return "analyze_symptoms", {"symptoms": message.split(":", 1)[1].strip()}

    if any(kw in txt for kw in _MEDICAL_KEYWORDS) and any(
        p in txt for p in ("i have", "experiencing", "feeling", "symptoms")
    ):
        return "analyze_symptoms", {"symptoms": message}

    return "chat", {"message": message}


# ───────────────────────── graceful shutdown ───────────────────────────────
def _shutdown() -> None:
    logger.info("Backend shutdown initiated …")
    try:
        fut = asyncio.run_coroutine_threadsafe(_client.close(), _backend_loop)
        fut.result(timeout=3)
    except Exception:  # noqa: BLE001
        logger.exception("Error while closing MCP connection.")
    finally:
        _backend_loop.call_soon_threadsafe(_backend_loop.stop)


atexit.register(_shutdown)

__all__ = ["get_mcp_response", "parse_message_for_action"]
