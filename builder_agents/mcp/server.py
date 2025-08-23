"""
MCP Server implementation for the agents package.
This provides a simple interface for MCP server communication.
"""

import asyncio
import json
import logging
import subprocess
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class MCPServerStdio:
    """MCP Server using stdio transport."""
    
    def __init__(self, params: Dict[str, Any], client_session_timeout_seconds: int = 120):
        """
        Initialize MCP server.
        
        Args:
            params: Server parameters with 'command' and 'args'
            client_session_timeout_seconds: Timeout for client sessions
        """
        self.params = params
        self.timeout = client_session_timeout_seconds
        self.process = None
        self._initialized = False
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
        
    async def initialize(self):
        """Initialize the MCP server process."""
        try:
            command = self.params.get("command", "python")
            args = self.params.get("args", [])
            
            # Start the MCP server process
            self.process = subprocess.Popen(
                [command] + args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            self._initialized = True
            logger.info(f"MCP server initialized: {command} {' '.join(args)}")
            
        except Exception as e:
            logger.error(f"Failed to initialize MCP server: {e}")
            raise
            
    async def close(self):
        """Close the MCP server process."""
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
            finally:
                self.process = None
                self._initialized = False
                
    def is_running(self) -> bool:
        """Check if the server is running."""
        return self._initialized and self.process and self.process.returncode is None
        
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Tool response
        """
        if not self.is_running():
            raise RuntimeError("MCP server is not running")
            
        try:
            # Create the tool call message
            message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            # Send the message
            message_str = json.dumps(message) + "\n"
            self.process.stdin.write(message_str)
            self.process.stdin.flush()
            
            # Read the response
            response_line = self.process.stdout.readline()
            if not response_line:
                raise RuntimeError("No response from MCP server")
                
            response = json.loads(response_line)
            
            # Check for errors
            if "error" in response:
                raise RuntimeError(f"MCP server error: {response['error']}")
                
            # Return the result
            return response.get("result", {})
            
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            raise


class MockMCPServerStdio:
    """Mock MCP server for testing and development."""
    
    def __init__(self, params: Dict[str, Any], client_session_timeout_seconds: int = 120):
        self.params = params
        self.timeout = client_session_timeout_seconds
        self._initialized = True
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
        
    def is_running(self) -> bool:
        return True
        
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Mock tool call that returns a simple response."""
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "agent": tool_name,
                        "response": f"Mock response from {tool_name}",
                        "confidence": 1.0,
                        "next_action": None,
                        "metadata": {}
                    })
                }
            ]
        }
