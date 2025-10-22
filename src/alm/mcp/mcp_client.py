#!/usr/bin/env python3
"""
MCP Client for Loki log querying.
Handles MCP session management and tool calling.
"""


import aiohttp


class MCPClient:
    def __init__(self, server_url):
        self.server_url = server_url
        self.session_id = None
        self.session: aiohttp.ClientSession = None
        self.tools = []

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def initialize(self):
        """Initialize MCP session"""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-chat", "version": "1.0.0"}
            }
        }

        try:
            async with self.session.post(
                self.server_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                response.raise_for_status()

                # Extract session ID from response headers
                self.session_id = response.headers.get("Mcp-Session-Id")
                if not self.session_id:
                    raise Exception("No session ID received from server")

                print(f"MCP session initialized: {self.session_id}")
                return await response.json()

        except Exception as e:
            print(f"Failed to initialize MCP session: {e}")
            return None

    async def get_tools(self):
        """Get available tools from MCP server"""
        if not self.session_id:
            print("No active session. Call initialize() first.")
            return None

        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }

        headers = {
            "Content-Type": "application/json",
            "Mcp-Session-Id": self.session_id
        }

        try:
            async with self.session.post(self.server_url, json=payload, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()

                if "result" in data and "tools" in data["result"]:
                    self.tools = data["result"]["tools"]
                    return self.tools
                return None
        except Exception as e:
            print(f"Error getting tools: {e}")
            return None

    async def call_tool(self, tool_name, arguments):
        """Call a tool on the MCP server"""
        if not self.session_id:
            print("No active session. Call initialize() first.")
            return None

        payload = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Mcp-Session-Id": self.session_id
        }

        try:
            async with self.session.post(self.server_url, json=payload, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()

                if "result" in data and "content" in data["result"]:
                    return data["result"]["content"][0]["text"]
                elif "error" in data:
                    return f"Error: {data['error']['message']}"
                return "No content returned"
        except Exception as e:
            return f"Error calling tool: {e}"