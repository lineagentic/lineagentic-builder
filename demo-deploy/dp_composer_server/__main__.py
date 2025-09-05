#!/usr/bin/env python3
"""
Entry point for the dp_composer_server package.

This module allows the package to be executed as a module using:
    python -m dp_composer_server

The package provides an MCP (Model Context Protocol) server with specialized tools
for data product development:

1. scoping_agent: Data product scoping and requirements expert
   - Define data product scope and boundaries
   - Gather requirements from user input
   - Extract required fields for data products

2. data_contract_agent: Data contract definition and validation expert
   - Define data contracts with required fields
   - Validate and extract field information
   - Extract metadata from user messages

Usage Examples:
    # Run with stdio transport (default)
    python -m dp_composer_server
    
    # Run with streamable HTTP transport
    python -m dp_composer_server --transport streamable-http
    
    # Run with SSE transport
    python -m dp_composer_server --transport sse

Environment Variables:
    OPENAI_API_KEY: Required OpenAI API key for the agents to function

For more information about MCP servers and transports, see:
    https://pypi.org/project/mcp/
"""

import sys
import argparse
from dp_composer_server import main

def parse_args():
    """Parse command line arguments for transport configuration."""
    parser = argparse.ArgumentParser(
        description="Run the dp_composer_server MCP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m dp_composer_server                    # Run with stdio transport
  python -m dp_composer_server --transport http   # Run with streamable-http transport
  python -m dp_composer_server --transport sse    # Run with SSE transport

Environment Variables:
  OPENAI_API_KEY    Required OpenAI API key for agent functionality
        """
    )
    
    parser.add_argument(
        '--transport',
        choices=['stdio', 'streamable-http', 'sse'],
        default='stdio',
        help='Transport method for the MCP server (default: stdio)'
    )
    
    parser.add_argument(
        '--host',
        default='localhost',
        help='Host for HTTP-based transports (default: localhost)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Port for HTTP-based transports (default: 8000)'
    )
    
    return parser.parse_args()

if __name__ == '__main__':
    try:
        args = parse_args()
        
        # For now, we'll use stdio transport as implemented in main()
        # Future enhancement: modify main() to accept transport parameters
        if args.transport != 'stdio':
            print(f"Warning: Transport '{args.transport}' not yet implemented in main().")
            print("Falling back to stdio transport.")
            print("To use other transports, modify the main() function in __init__.py")
        
        # Call the main function from the package
        main()
        
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)
