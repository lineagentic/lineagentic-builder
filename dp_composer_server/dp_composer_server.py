import logging
import sys
import json
import uuid
import re
from datetime import datetime
from pathlib import Path

# Configure logging to show INFO level and above in console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # This ensures output goes to console
        logging.FileHandler('dp_server.log')  # Optional: also log to file
    ]
)

# Set MCP loggers to INFO level so we can see what's happening
logging.getLogger('mcp').setLevel(logging.INFO)
logging.getLogger('mcp.server').setLevel(logging.INFO)

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.server.fastmcp import FastMCP
from typing import Dict, Any
from dp_composer_server.datacontract_agent.data_contract_agent import DataContractAgentStructured, Message
from dp_composer_server.scoping_agent.scoping_agent import ScopingAgentStructured
from openai import OpenAI
import os

mcp = FastMCP("dp_builder_server")

# Directory for session-based conversation states


# Initialize OpenAI client
def get_openai_client():
    """Get OpenAI client with proper error handling."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    return OpenAI(api_key=api_key)

@mcp.tool()
async def scoping_agent(messages: str) -> Dict[str, Any]:
    """Data product scoping and requirements expert
    
    Capabilities:
    - scope_definition: Define data product scope and boundaries
    - requirements_gathering: Gather requirements from user input
    - field_extraction: Extract required fields for data products
    """

    openai_client = get_openai_client()
    agent = ScopingAgentStructured(openai_client=openai_client)
    
    # Parse the messages string to extract user_message and conversation_state
    # Extract user message
    user_message_match = re.search(r'User Message:\s*(.+?)(?=\n\s*Conversation State:|$)', messages, re.DOTALL)
    user_message = user_message_match.group(1).strip() if user_message_match else ""
    
    # Extract conversation state
    conversation_state_match = re.search(r'Conversation State:\s*(.+?)$', messages, re.DOTALL)
    conversation_state_str = conversation_state_match.group(1).strip() if conversation_state_match else "{}"
    
    # Parse conversation state from string to dict
    try:
        conversation_state = json.loads(conversation_state_str)
    except json.JSONDecodeError:
        # If parsing fails, create a default state
        conversation_state = {"session_id": None, "data_product": {}, "history": []}
    
    # Process message with current conversation state
    message = Message("user", user_message)
    result = await agent.handle_async(conversation_state, message)

            
    return {
        "reply": result["reply"],
        "confidence": result["confidence"],
        "next_action": result["next_action"],
        "metadata": result["metadata"],
        "extracted_data": result["extracted_data"],
        "missing_fields": result["missing_fields"]
    }
        


@mcp.tool()
async def data_contract_agent(messages: str) -> Dict[str, Any]:
    """Data contract definition and validation expert
    
    Capabilities:
    - contract_definition: Define data contracts with required fields
    - field_validation: Validate and extract field information
    - metadata_extraction: Extract metadata from user messages
    """

        
    # Create agent instance with OpenAI client
    openai_client = get_openai_client()
    agent = DataContractAgentStructured(openai_client=openai_client)
    
    # Parse the messages string to extract user_message and conversation_state
    # Extract user message
    user_message_match = re.search(r'User Message:\s*(.+?)(?=\n\s*Conversation State:|$)', messages, re.DOTALL)
    user_message = user_message_match.group(1).strip() if user_message_match else ""
    
    # Extract conversation state
    conversation_state_match = re.search(r'Conversation State:\s*(.+?)$', messages, re.DOTALL)
    conversation_state_str = conversation_state_match.group(1).strip() if conversation_state_match else "{}"
    
    # Parse conversation state from string to dict
    try:
        conversation_state = json.loads(conversation_state_str)
    except json.JSONDecodeError:
        # If parsing fails, create a default state
        conversation_state = {"session_id": None, "data_product": {}, "history": []}
    
    # Process message with current conversation state
    message = Message("user", user_message)
    result = await agent.handle_async(conversation_state, message)

        
    return {
        "reply": result["reply"],
        "confidence": result["confidence"],
        "next_action": result["next_action"],
        "metadata": result["metadata"],
        "extracted_data": result["extracted_data"],
        "missing_fields": result["missing_fields"]
    }
        



if __name__ == "__main__":
    mcp.run(transport='stdio')
