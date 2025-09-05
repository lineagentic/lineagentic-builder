# dp_composer_server package

"""
dp_composer_server - MCP Server for Data Product Development

This package provides an MCP (Model Context Protocol) server with specialized tools
for data product development:

1. scoping_agent: Data product scoping and requirements expert
   - Define data product scope and boundaries
   - Gather requirements from user input
   - Extract required fields for data products

2. data_contract_agent: Data contract definition and validation expert
   - Define data contracts with required fields
   - Validate and extract field information
   - Extract metadata from user messages

Usage:
    # Run as a module
    python -m dp_composer_server
    
    # Run the server directly
    python dp_composer_server/dp_composer_server.py

Environment Variables:
    OPENAI_API_KEY: Required OpenAI API key for the agents to function

For more information about MCP servers, see:
    https://pypi.org/project/mcp/
"""

from dp_composer_server.dp_composer_server import main

__version__ = "0.1.0"
__all__ = ["main"]
