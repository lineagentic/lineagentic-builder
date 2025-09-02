import os
from dotenv import load_dotenv

load_dotenv(override=True)

# MCP server parameters for the agentic orchestration server
dp_builder_mcp_server_params = [
    {
        "command": "python", 
        "args": ["dp_server/dp_server.py"],
        "env": {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "PYTHONPATH": os.getenv("PYTHONPATH", ""),
            "PATH": os.getenv("PATH", "")
        }
    },
]
