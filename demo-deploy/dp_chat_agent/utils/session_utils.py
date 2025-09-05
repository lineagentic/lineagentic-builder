import logging
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


STATE_DIR = Path(__file__).parent.parent / "sessions"

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
    

    
    logging.info(f"Created new clean session: {session_id}")
    return session_id