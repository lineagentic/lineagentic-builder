import logging
import sys
import json
import uuid
from datetime import datetime
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

# Directory for session-based conversation states
STATE_DIR = Path(__file__).parent / "sessions"

# Ensure sessions directory exists
STATE_DIR.mkdir(exist_ok=True)

def get_session_file_path(session_id: str) -> Path:
    """Get the file path for a specific session."""
    return STATE_DIR / f"conversation_state_{session_id}.json"

def load_conversation_state(session_id: str = None) -> Dict[str, Any]:
    """Load conversation state from JSON file for a specific session."""
    if not session_id:
        # Fallback to default state if no session ID provided
        return {
            "session_id": None,
            "data_product": {},
            "history": []
        }
    
    session_file = get_session_file_path(session_id)
    try:
        if session_file.exists():
            with open(session_file, 'r') as f:
                state = json.load(f)
                
                # Validate the session file
                if not isinstance(state, dict):
                    logging.warning(f"Invalid session file format for {session_id}")
                    return _create_default_state(session_id)
                
                # Check if this is a valid session file
                if "session_id" not in state or state["session_id"] != session_id:
                    logging.warning(f"Session ID mismatch in file for {session_id}")
                    return _create_default_state(session_id)
                
                # Ensure session_id is set in the loaded state
                state["session_id"] = session_id
                return state
    except Exception as e:
        logging.warning(f"Could not load conversation state for session {session_id}: {e}")
    
    # Return default state for new session
    return _create_default_state(session_id)

def _create_default_state(session_id: str) -> Dict[str, Any]:
    """Create a default state for a new session."""
    return {
        "session_id": session_id,
        "data_product": {},
        "history": []
    }

def cleanup_invalid_sessions():
    """Clean up invalid session files and ensure clean state."""
    try:
        session_files = list(STATE_DIR.glob("conversation_state_*.json"))
        cleaned_count = 0
        
        for session_file in session_files:
            try:
                with open(session_file, 'r') as f:
                    state = json.load(f)
                
                # Check if file is valid
                if not isinstance(state, dict) or "session_id" not in state:
                    logging.warning(f"Removing invalid session file: {session_file}")
                    session_file.unlink()
                    cleaned_count += 1
                    continue
                
                # Extract session ID from filename
                filename_session_id = session_file.stem.replace("conversation_state_", "")
                
                # Check if filename matches session_id in file
                if state["session_id"] != filename_session_id:
                    logging.warning(f"Removing session file with ID mismatch: {session_file}")
                    session_file.unlink()
                    cleaned_count += 1
                    
            except Exception as e:
                logging.warning(f"Error reading session file {session_file}: {e}")
                # Remove corrupted files
                session_file.unlink()
                cleaned_count += 1
        
        if cleaned_count > 0:
            logging.info(f"Cleaned up {cleaned_count} invalid session files")
        
    except Exception as e:
        logging.error(f"Error during session cleanup: {e}")

# Clean up any invalid sessions on startup
cleanup_invalid_sessions()

def save_conversation_state(state: Dict[str, Any], session_id: str):
    """Save conversation state to JSON file for a specific session."""
    if not session_id:
        logging.error("Cannot save conversation state without session_id")
        return
    
    session_file = get_session_file_path(session_id)
    try:
        # Ensure session_id is set in the state
        state["session_id"] = session_id
        
        # Add timestamps
        current_time = datetime.now().isoformat()
        if "created_at" not in state:
            state["created_at"] = current_time
        state["last_updated"] = current_time
        
        with open(session_file, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logging.error(f"Could not save conversation state for session {session_id}: {e}")

def create_new_session() -> str:
    """Create a new session and return the session ID."""
    session_id = str(uuid.uuid4())
    
    # Validate that we got a proper UUID
    try:
        uuid.UUID(session_id)
    except ValueError:
        logging.error(f"Invalid UUID generated: {session_id}")
        # Generate a new one
        session_id = str(uuid.uuid4())
    
    # Initialize completely clean state for new session
    initial_state = {
        "session_id": session_id,
        "data_product": {},
        "history": []
    }
    
    # Save the clean state
    save_conversation_state(initial_state, session_id)
    
    logging.info(f"Created new clean session: {session_id}")
    return session_id

# Initialize OpenAI client
def get_openai_client():
    """Get OpenAI client with proper error handling."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    return OpenAI(api_key=api_key)

@mcp.tool()
async def scoping_agent(user_message: str, session_id: str) -> Dict[str, Any]:
    """Data product scoping and requirements expert
    
    Capabilities:
    - scope_definition: Define data product scope and boundaries
    - requirements_gathering: Gather requirements from user input
    - field_extraction: Extract required fields for data products
    """
    try:
        # Load conversation state for this session
        conversation_state = load_conversation_state(session_id)
        
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
            save_conversation_state(conversation_state, session_id)
        else:
            logging.info(f"No extracted data in result: {result}")
        
        # Update history
        conversation_state["history"].append({"role": "user", "content": user_message})
        conversation_state["history"].append({"role": "assistant", "content": result["reply"]})
        # Save the updated history to file
        save_conversation_state(conversation_state, session_id)
        
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
async def data_contract_agent(user_message: str, session_id: str) -> Dict[str, Any]:
    """Data contract definition and validation expert
    
    Capabilities:
    - contract_definition: Define data contracts with required fields
    - field_validation: Validate and extract field information
    - metadata_extraction: Extract metadata from user messages
    """
    try:
        # Load conversation state for this session
        conversation_state = load_conversation_state(session_id)
        
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
            save_conversation_state(conversation_state, session_id)
        
        # Update history
        conversation_state["history"].append({"role": "user", "content": user_message})
        conversation_state["history"].append({"role": "assistant", "content": result["reply"]})
        # Save the updated history to file
        save_conversation_state(conversation_state, session_id)
        
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
    description="Get current conversation state and history for a session"
)
async def get_conversation_state(session_id: str) -> Dict[str, Any]:
    """Get current conversation state and history for a specific session"""
    conversation_state = load_conversation_state(session_id)
    logging.info(f"Getting conversation state for session {session_id}: {conversation_state}")
    return conversation_state

@mcp.tool(
    name="create_session",
    description="Create a new chat session"
)
async def create_session() -> Dict[str, Any]:
    """Create a new chat session and return the session ID"""
    session_id = create_new_session()
    return {"session_id": session_id, "message": "New session created successfully"}

@mcp.tool(
    name="reset_conversation",
    description="Reset conversation state for a session"
)
async def reset_conversation(session_id: str) -> Dict[str, Any]:
    """Reset conversation state for a specific session"""
    reset_state = {
        "session_id": session_id,
        "data_product": {},
        "history": []
    }
    save_conversation_state(reset_state, session_id)
    return {"message": f"Conversation reset successfully for session {session_id}"}

@mcp.tool(
    name="list_sessions",
    description="List all available sessions"
)
async def list_sessions() -> Dict[str, Any]:
    """List all available sessions"""
    try:
        session_files = list(STATE_DIR.glob("conversation_state_*.json"))
        sessions = []
        
        for session_file in session_files:
            try:
                with open(session_file, 'r') as f:
                    state = json.load(f)
                
                # Validate session file
                if not isinstance(state, dict) or "session_id" not in state:
                    logging.warning(f"Skipping invalid session file: {session_file}")
                    continue
                
                # Extract session ID from filename
                filename_session_id = session_file.stem.replace("conversation_state_", "")
                
                # Check if filename matches session_id in file
                if state["session_id"] != filename_session_id:
                    logging.warning(f"Skipping session file with ID mismatch: {session_file}")
                    continue
                
                # Only include valid sessions
                sessions.append({
                    "session_id": state["session_id"],
                    "created_at": state.get("created_at", "unknown"),
                    "last_updated": state.get("last_updated", "unknown"),
                    "message_count": len(state.get("history", [])),
                    "data_product_name": state.get("data_product", {}).get("name", "unnamed")
                })
                
            except Exception as e:
                logging.warning(f"Could not read session file {session_file}: {e}")
                continue
        
        return {
            "sessions": sessions,
            "total_valid_sessions": len(sessions),
            "message": f"Found {len(sessions)} valid sessions"
        }
        
    except Exception as e:
        logging.error(f"Error listing sessions: {e}")
        return {"error": f"Could not list sessions: {str(e)}"}

if __name__ == "__main__":
    mcp.run(transport='stdio')
