import logging
import sys
import json
from pathlib import Path

# Configure logging to suppress verbose output
logging.basicConfig(level=logging.WARNING)
logging.getLogger('mcp').setLevel(logging.WARNING)
logging.getLogger('mcp.server').setLevel(logging.WARNING)

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.server.fastmcp import FastMCP
from typing import Dict, Any
from dp_agents.datacontract_agent.data_contract_agent import DataContractAgentStructured, Message
from dp_agents.scoping_agent.scoping_agent import ScopingAgentStructured
from openai import OpenAI
import os

mcp = FastMCP("dp_builder_server")

# File path for persistent conversation state
STATE_FILE = Path(__file__).parent / "conversation_state.json"

def load_conversation_state() -> Dict[str, Any]:
    """Load conversation state from JSON file."""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logging.warning(f"Could not load conversation state: {e}")
    
    # Return default state if file doesn't exist or can't be loaded
    return {
        "data_product": {},
        "history": []
    }

def save_conversation_state(state: Dict[str, Any]):
    """Save conversation state to JSON file."""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logging.error(f"Could not save conversation state: {e}")

# Load initial conversation state
conversation_state = load_conversation_state()

# Initialize OpenAI client
def get_openai_client():
    """Get OpenAI client with proper error handling."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    return OpenAI(api_key=api_key)

@mcp.tool()
async def scoping_agent(user_message: str) -> Dict[str, Any]:
    """Data product scoping and requirements expert
    
    Capabilities:
    - scope_definition: Define data product scope and boundaries
    - requirements_gathering: Gather requirements from user input
    - field_extraction: Extract required fields for data products
    """
    global conversation_state
    
    try:
        # Create agent instance with OpenAI client
        openai_client = get_openai_client()
        agent = ScopingAgentStructured(openai_client=openai_client)
        
        # Process message with current conversation state
        message = Message("user", user_message)
        result = await agent.handle_async(conversation_state, message)
        
        # Update conversation state with new information
        if result.get("extracted_data"):
            data_product = conversation_state.get("data_product", {})
            logging.info(f"Updating conversation state with extracted data: {result['extracted_data']}")
            for key, value in result["extracted_data"].items():
                if value:
                    data_product[key] = value
            conversation_state["data_product"] = data_product
            logging.info(f"Updated conversation state: {conversation_state}")
            # Save the updated state to file
            save_conversation_state(conversation_state)
        else:
            logging.info(f"No extracted data in result: {result}")
        
        # Update history
        conversation_state["history"].append({"role": "user", "content": user_message})
        conversation_state["history"].append({"role": "assistant", "content": result["reply"]})
        # Save the updated history to file
        save_conversation_state(conversation_state)
        
        return result
        
    except Exception as e:
        error_msg = f"Error in scoping agent: {str(e)}"
        logging.error(error_msg)
        return {
            "reply": f"I encountered an error while processing your request: {str(e)}. Please try again.",
            "confidence": 0.0,
            "next_action": "retry",
            "metadata": {"error": str(e)},
            "extracted_data": {},
            "missing_fields": []
        }

@mcp.tool()
async def data_contract_agent(user_message: str) -> Dict[str, Any]:
    """Data contract definition and validation expert
    
    Capabilities:
    - contract_definition: Define data contracts with required fields
    - field_validation: Validate and extract field information
    - metadata_extraction: Extract metadata from user messages
    """
    global conversation_state
    
    try:
        # Create agent instance with OpenAI client
        openai_client = get_openai_client()
        agent = DataContractAgentStructured(openai_client=openai_client)
        
        # Process message with current conversation state
        message = Message("user", user_message)
        result = await agent.handle_async(conversation_state, message)
        
        # Update conversation state with new information
        if result.get("extracted_data"):
            data_product = conversation_state.get("data_product", {})
            for key, value in result["extracted_data"].items():
                if value:
                    data_product[key] = value
            conversation_state["data_product"] = data_product
            # Save the updated state to file
            save_conversation_state(conversation_state)
        
        # Update history
        conversation_state["history"].append({"role": "user", "content": user_message})
        conversation_state["history"].append({"role": "assistant", "content": result["reply"]})
        # Save the updated history to file
        save_conversation_state(conversation_state)
        
        return result
        
    except Exception as e:
        error_msg = f"Error in data contract agent: {str(e)}"
        logging.error(error_msg)
        return {
            "reply": f"I encountered an error while processing your request: {str(e)}. Please try again.",
            "confidence": 0.0,
            "next_action": "retry",
            "metadata": {"error": str(e)},
            "extracted_data": {},
            "missing_fields": []
        }

@mcp.tool(
    name="get_conversation_state",
    description="Get current conversation state and history"
)
async def get_conversation_state() -> Dict[str, Any]:
    """Get current conversation state and history"""
    logging.info(f"Getting conversation state: {conversation_state}")
    return conversation_state

@mcp.tool(
    name="reset_conversation",
    description="Reset conversation state"
)
async def reset_conversation() -> Dict[str, Any]:
    """Reset conversation state"""
    global conversation_state
    conversation_state = {
        "data_product": {},
        "history": []
    }
    save_conversation_state(conversation_state) # Save the reset state
    return {"message": "Conversation reset successfully"}

if __name__ == "__main__":
    mcp.run(transport='stdio')
