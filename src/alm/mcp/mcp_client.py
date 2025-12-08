#!/usr/bin/env python3
"""
MCP Client for Loki log querying.
Handles MCP session management and tool calling.
"""

import httpx

from alm.utils.logger import get_logger

logger = get_logger(__name__)


class MCPClient:
    def __init__(self, server_url):
        self.server_url = server_url
        self.session_id = None
        self.client: httpx.AsyncClient = None
        self.tools = []

    async def __aenter__(self):
        self.client = httpx.AsyncClient()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def initialize(self):
        """Initialize MCP session"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-chat", "version": "1.0.0"},
            },
        }

        try:
            response = await self.client.post(
                self.server_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            # Extract session ID from response headers
            self.session_id = response.headers.get("Mcp-Session-Id")
            if not self.session_id:
                raise Exception("No session ID received from server")

            logger.info("MCP session initialized: %s", self.session_id)
            return response.json()

        except Exception as e:
            logger.error("Failed to initialize MCP session: %s", e)
            return None

    async def get_tools(self):
        """Get available tools from MCP server"""
        if not self.session_id:
            logger.warning("No active session. Call initialize() first.")
            return None

        payload = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

        headers = {
            "Content-Type": "application/json",
            "Mcp-Session-Id": self.session_id,
        }

        try:
            response = await self.client.post(
                self.server_url, json=payload, headers=headers
            )
            response.raise_for_status()
            data = response.json()

            if "result" in data and "tools" in data["result"]:
                self.tools = data["result"]["tools"]
                return self.tools
            return None
        except Exception as e:
            logger.error("Error getting tools: %s", e)
            return None

    async def call_tool(self, tool_name, arguments):
        """Call a tool on the MCP server"""
        if not self.session_id:
            logger.warning("No active session. Call initialize() first.")
            return None

        payload = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

        headers = {
            "Content-Type": "application/json",
            "Mcp-Session-Id": self.session_id,
        }

        try:
            response = await self.client.post(
                self.server_url, json=payload, headers=headers
            )
            response.raise_for_status()
            data = response.json()

            if "result" in data and "content" in data["result"]:
                return data["result"]["content"][0]["text"]
            elif "error" in data:
                return f"Error: {data['error']['message']}"
            return "No content returned"
        except Exception as e:
            return f"Error calling tool: {e}"
