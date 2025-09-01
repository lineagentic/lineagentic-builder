import os
from dotenv import load_dotenv

load_dotenv(override=True)

# MCP server parameters for the agentic orchestration server
agentic_mcp_server_params = [
    {
        "command": "python", 
        "args": ["dp_server/dp_builder_server.py"]
    },
]
