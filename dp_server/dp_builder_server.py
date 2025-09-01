"""
MCP Server that exposes scoping agent as a tool.
This server provides access to the scoping agent for data product creation.
"""
import logging
import sys
import os
from typing import Dict, Any

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging to suppress verbose output
logging.basicConfig(level=logging.WARNING)
logging.getLogger('mcp').setLevel(logging.WARNING)
logging.getLogger('mcp.server').setLevel(logging.WARNING)

from mcp.server.fastmcp import FastMCP
from openai import OpenAI

# Import only the scoping agent
from dp_agents.scoping_agent.scoping_agent import ScopingAgentStructured
from dp_agents.scoping_agent.scoping_agent import Message

# Initialize MCP server
mcp = FastMCP("scoping_agent_server")

# Global conversation state
conversation_state = {
    "data_product": {},
    "history": []
}

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
openai_client = None
if api_key:
    openai_client = OpenAI(api_key=api_key)
    logging.info("OpenAI API key loaded from environment")
else:
    logging.warning("OPENAI_API_KEY not found in environment variables")

# Initialize scoping agent
scoping_agent_instance = None
try:
    if openai_client:
        scoping_agent_instance = ScopingAgentStructured(openai_client=openai_client)
        logging.info("Successfully initialized scoping agent with OpenAI client")
    else:
        logging.warning("No OpenAI client available - scoping agent will not be initialized")
except Exception as e:
    logging.warning(f"Could not initialize scoping agent: {e}")

@mcp.tool()
async def scoping_agent(message: str) -> Dict[str, Any]:
    """
    Scoping agent for defining data product basic scope.
    
    Args:
        message: User message containing scoping information
        
    Returns:
        Agent response with reply, confidence, next_action, and metadata
    """
    try:
        if scoping_agent_instance is None:
            return {
                "agent": "scoping",
                "error": "Agent not initialized - OPENAI_API_KEY required",
                "response": "Please set OPENAI_API_KEY environment variable to use this agent",
                "confidence": 0.0
            }
        
        msg = Message("user", message)
        result = await scoping_agent_instance.handle_async(conversation_state, msg)
        
        # Update conversation state
        conversation_state["history"].append({"role": "user", "content": message})
        conversation_state["history"].append({"role": "assistant", "content": result["reply"]})
        
        return {
            "agent": "scoping",
            "response": result["reply"],
            "confidence": result["confidence"],
            "next_action": result["next_action"],
            "metadata": result["metadata"],
            "current_state": conversation_state
        }
    except Exception as e:
        return {
            "agent": "scoping",
            "error": str(e),
            "response": f"Error in scoping agent: {str(e)}",
            "confidence": 0.0
        }

@mcp.tool()
def get_conversation_state() -> Dict[str, Any]:
    """
    Get the current conversation state including data product information.
    
    Returns:
        Current conversation state
    """
    return {
        "data_product": conversation_state.get("data_product", {}),
        "history": conversation_state.get("history", []),
        "agent_available": scoping_agent_instance is not None
    }

@mcp.tool()
def reset_conversation() -> Dict[str, Any]:
    """
    Reset the conversation state to start fresh.
    
    Returns:
        Confirmation message
    """
    global conversation_state
    conversation_state = {
        "data_product": {},
        "history": []
    }
    
    return {
        "message": "Conversation state reset successfully",
        "agent_available": scoping_agent_instance is not None
    }

if __name__ == "__main__":
    mcp.run(transport='stdio')
