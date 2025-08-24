"""
MCP Server that exposes agentic orchestration agents as tools.
This server provides access to all the structured agents for data product creation.
"""
import logging
import sys
import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging to suppress verbose output
logging.basicConfig(level=logging.WARNING)
logging.getLogger('mcp').setLevel(logging.WARNING)
logging.getLogger('mcp.server').setLevel(logging.WARNING)

from mcp.server.fastmcp import FastMCP
from openai import OpenAI

# Import the agents
from builder_agents.scoping_agent_structured import ScopingAgentStructured
from builder_agents.schema_contract_agent_structured import SchemaContractAgentStructured
from builder_agents.policy_agent_structured import PolicyAgentStructured
from builder_agents.provisioning_agent_structured import ProvisioningAgentStructured
from builder_agents.docs_agent_structured import DocsAgentStructured
from builder_agents.catalog_agent_structured import CatalogAgentStructured
from builder_agents.observability_agent_structured import ObservabilityAgentStructured
from builder_agents.base_structured import Message

# Initialize MCP server
mcp = FastMCP("agentic_orchestration_server")

# Global conversation state
conversation_state = {
    "data_product": {},
    "policy_pack": {},
    "history": []
}

# Session management
current_session_id = None
sessions_dir = "sessions"

def ensure_sessions_directory():
    """Ensure the sessions directory exists."""
    if not os.path.exists(sessions_dir):
        os.makedirs(sessions_dir)

def generate_session_id() -> str:
    """Generate a unique session ID."""
    return str(uuid.uuid4())

def get_session_filename(session_id: str) -> str:
    """Get the filename for a session."""
    return os.path.join(sessions_dir, f"session_{session_id}.json")

def save_session_state(session_id: str, state: Dict[str, Any]) -> bool:
    """Save session state to file."""
    try:
        ensure_sessions_directory()
        filename = get_session_filename(session_id)
        
        session_data = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "state": state
        }
        
        with open(filename, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving session state: {e}")
        return False

def load_session_state(session_id: str) -> Optional[Dict[str, Any]]:
    """Load session state from file."""
    try:
        filename = get_session_filename(session_id)
        if not os.path.exists(filename):
            return None
        
        with open(filename, 'r') as f:
            session_data = json.load(f)
        
        # Update last_updated timestamp
        session_data["last_updated"] = datetime.now().isoformat()
        
        # Save the updated timestamp
        with open(filename, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        return session_data["state"]
    except Exception as e:
        print(f"Error loading session state: {e}")
        return None

def list_sessions() -> list:
    """List all available sessions."""
    try:
        ensure_sessions_directory()
        sessions = []
        for filename in os.listdir(sessions_dir):
            if filename.startswith("session_") and filename.endswith(".json"):
                session_id = filename[8:-5]  # Remove "session_" prefix and ".json" suffix
                filepath = os.path.join(sessions_dir, filename)
                
                try:
                    with open(filepath, 'r') as f:
                        session_data = json.load(f)
                    
                    sessions.append({
                        "session_id": session_id,
                        "created_at": session_data.get("created_at"),
                        "last_updated": session_data.get("last_updated"),
                        "data_product_name": session_data.get("state", {}).get("data_product", {}).get("name", "Unnamed")
                    })
                except Exception as e:
                    print(f"Error reading session file {filename}: {e}")
        
        # Sort by last_updated (most recent first)
        sessions.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
        return sessions
    except Exception as e:
        print(f"Error listing sessions: {e}")
        return []

def delete_session(session_id: str) -> bool:
    """Delete a session file."""
    try:
        filename = get_session_filename(session_id)
        if os.path.exists(filename):
            os.remove(filename)
            return True
        return False
    except Exception as e:
        print(f"Error deleting session: {e}")
        return False

def _build_conversation_context(state: Dict[str, Any]) -> str:
    """Build conversation context string for agents."""
    context_parts = []
    
    # Add data product state
    data_product = state.get("data_product", {})
    if data_product:
        context_parts.append("Data Product State:")
        for key, value in data_product.items():
            context_parts.append(f"  {key}: {value}")
    
    # Add policy pack state
    policy_pack = state.get("policy_pack", {})
    if policy_pack:
        context_parts.append("Policy Pack State:")
        for key, value in policy_pack.items():
            context_parts.append(f"  {key}: {value}")
    
    # Add recent history
    history = state.get("history", [])
    if history:
        context_parts.append("Recent Conversation History:")
        for entry in history[-6:]:  # Last 6 entries
            role = entry.get("role", "unknown")
            content = entry.get("content", "")[:200]  # Truncate long messages
            context_parts.append(f"  {role}: {content}")
    
    return "\n".join(context_parts) if context_parts else "No previous context available."

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

# Initialize agents
agents = {}
try:
    if openai_client:
        agents = {
            "scoping": ScopingAgentStructured(openai_client=openai_client),
            "schema_contract": SchemaContractAgentStructured(openai_client=openai_client),
            "policy": PolicyAgentStructured(openai_client=openai_client),
            "provisioning": ProvisioningAgentStructured(openai_client=openai_client),
            "docs": DocsAgentStructured(openai_client=openai_client),
            "catalog": CatalogAgentStructured(openai_client=openai_client),
            "observability": ObservabilityAgentStructured(openai_client=openai_client)
        }
        logging.info(f"Successfully initialized {len(agents)} agents with OpenAI client")
    else:
        logging.warning("No OpenAI client available - agents will not be initialized")
        agents = {}
except Exception as e:
    logging.warning(f"Could not initialize agents: {e}")
    # Initialize with empty dict - agents will be created on-demand
    agents = {}

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
        if "scoping" not in agents:
            return {
                "agent": "scoping",
                "error": "Agent not initialized - OPENAI_API_KEY required",
                "response": "Please set OPENAI_API_KEY environment variable to use this agent",
                "confidence": 0.0
            }
        
        agent = agents["scoping"]
        msg = Message("user", message)
        result = await agent.handle_async(conversation_state, msg)
        
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
async def schema_contract_agent(message: str) -> Dict[str, Any]:
    """
    Schema contract agent for defining data product schema and contracts.
    
    Args:
        message: User message containing schema information
        
    Returns:
        Agent response with reply, confidence, next_action, and metadata
    """
    try:
        if "schema_contract" not in agents:
            return {
                "agent": "schema_contract",
                "error": "Agent not initialized - OPENAI_API_KEY required",
                "response": "Please set OPENAI_API_KEY environment variable to use this agent",
                "confidence": 0.0
            }
        
        agent = agents["schema_contract"]
        msg = Message("user", message)
        result = await agent.handle_async(conversation_state, msg)
        
        # Update conversation state
        conversation_state["history"].append({"role": "user", "content": message})
        conversation_state["history"].append({"role": "assistant", "content": result["reply"]})
        
        return {
            "agent": "schema_contract",
            "response": result["reply"],
            "confidence": result["confidence"],
            "next_action": result["next_action"],
            "metadata": result["metadata"],
            "current_state": conversation_state
        }
    except Exception as e:
        return {
            "agent": "schema_contract",
            "error": str(e),
            "response": f"Error in schema contract agent: {str(e)}",
            "confidence": 0.0
        }

@mcp.tool()
async def policy_agent(message: str) -> Dict[str, Any]:
    """
    Policy agent for defining data product policies and governance.
    
    Args:
        message: User message containing policy information
        
    Returns:
        Agent response with reply, confidence, next_action, and metadata
    """
    try:
        if "policy" not in agents:
            return {
                "agent": "policy",
                "error": "Agent not initialized - OPENAI_API_KEY required",
                "response": "Please set OPENAI_API_KEY environment variable to use this agent",
                "confidence": 0.0
            }
        
        agent = agents["policy"]
        msg = Message("user", message)
        result = await agent.handle_async(conversation_state, msg)
        
        # Update conversation state
        conversation_state["history"].append({"role": "user", "content": message})
        conversation_state["history"].append({"role": "assistant", "content": result["reply"]})
        
        return {
            "agent": "policy",
            "response": result["reply"],
            "confidence": result["confidence"],
            "next_action": result["next_action"],
            "metadata": result["metadata"],
            "current_state": conversation_state
        }
    except Exception as e:
        return {
            "agent": "policy",
            "error": str(e),
            "response": f"Error in policy agent: {str(e)}",
            "confidence": 0.0
        }

@mcp.tool()
async def provisioning_agent(message: str) -> Dict[str, Any]:
    """
    Provisioning agent for infrastructure and deployment planning.
    
    Args:
        message: User message containing provisioning information
        
    Returns:
        Agent response with reply, confidence, next_action, and metadata
    """
    try:
        if "provisioning" not in agents:
            return {
                "agent": "provisioning",
                "error": "Agent not initialized - OPENAI_API_KEY required",
                "response": "Please set OPENAI_API_KEY environment variable to use this agent",
                "confidence": 0.0
            }
        
        agent = agents["provisioning"]
        msg = Message("user", message)
        result = await agent.handle_async(conversation_state, msg)
        
        # Update conversation state
        conversation_state["history"].append({"role": "user", "content": message})
        conversation_state["history"].append({"role": "assistant", "content": result["reply"]})
        
        return {
            "agent": "provisioning",
            "response": result["reply"],
            "confidence": result["confidence"],
            "next_action": result["next_action"],
            "metadata": result["metadata"],
            "current_state": conversation_state
        }
    except Exception as e:
        return {
            "agent": "provisioning",
            "error": str(e),
            "response": f"Error in provisioning agent: {str(e)}",
            "confidence": 0.0
        }

@mcp.tool()
async def docs_agent(message: str) -> Dict[str, Any]:
    """
    Documentation agent for generating data product documentation.
    
    Args:
        message: User message containing documentation requirements
        
    Returns:
        Agent response with reply, confidence, next_action, and metadata
    """
    try:
        if "docs" not in agents:
            return {
                "agent": "docs",
                "error": "Agent not initialized - OPENAI_API_KEY required",
                "response": "Please set OPENAI_API_KEY environment variable to use this agent",
                "confidence": 0.0
            }
        
        agent = agents["docs"]
        msg = Message("user", message)
        result = await agent.handle_async(conversation_state, msg)
        
        # Update conversation state
        conversation_state["history"].append({"role": "user", "content": message})
        conversation_state["history"].append({"role": "assistant", "content": result["reply"]})
        
        return {
            "agent": "docs",
            "response": result["reply"],
            "confidence": result["confidence"],
            "next_action": result["next_action"],
            "metadata": result["metadata"],
            "current_state": conversation_state
        }
    except Exception as e:
        return {
            "agent": "docs",
            "error": str(e),
            "response": f"Error in docs agent: {str(e)}",
            "confidence": 0.0
        }

@mcp.tool()
async def catalog_agent(message: str) -> Dict[str, Any]:
    """
    Catalog agent for metadata management and cataloging.
    
    Args:
        message: User message containing catalog information
        
    Returns:
        Agent response with reply, confidence, next_action, and metadata
    """
    try:
        if "catalog" not in agents:
            return {
                "agent": "catalog",
                "error": "Agent not initialized - OPENAI_API_KEY required",
                "response": "Please set OPENAI_API_KEY environment variable to use this agent",
                "confidence": 0.0
            }
        
        agent = agents["catalog"]
        msg = Message("user", message)
        result = await agent.handle_async(conversation_state, msg)
        
        # Update conversation state
        conversation_state["history"].append({"role": "user", "content": message})
        conversation_state["history"].append({"role": "assistant", "content": result["reply"]})
        
        return {
            "agent": "catalog",
            "response": result["reply"],
            "confidence": result["confidence"],
            "next_action": result["next_action"],
            "metadata": result["metadata"],
            "current_state": conversation_state
        }
    except Exception as e:
        return {
            "agent": "catalog",
            "error": str(e),
            "response": f"Error in catalog agent: {str(e)}",
            "confidence": 0.0
        }

@mcp.tool()
async def observability_agent(message: str) -> Dict[str, Any]:
    """
    Observability agent for monitoring and alerting setup.
    
    Args:
        message: User message containing observability requirements
        
    Returns:
        Agent response with reply, confidence, next_action, and metadata
    """
    try:
        if "observability" not in agents:
            return {
                "agent": "observability",
                "error": "Agent not initialized - OPENAI_API_KEY required",
                "response": "Please set OPENAI_API_KEY environment variable to use this agent",
                "confidence": 0.0
            }
        
        agent = agents["observability"]
        msg = Message("user", message)
        result = await agent.handle_async(conversation_state, msg)
        
        # Update conversation state
        conversation_state["history"].append({"role": "user", "content": message})
        conversation_state["history"].append({"role": "assistant", "content": result["reply"]})
        
        return {
            "agent": "observability",
            "response": result["reply"],
            "confidence": result["confidence"],
            "next_action": result["next_action"],
            "metadata": result["metadata"],
            "current_state": conversation_state
        }
    except Exception as e:
        return {
            "agent": "observability",
            "error": str(e),
            "response": f"Error in observability agent: {str(e)}",
            "confidence": 0.0
        }

@mcp.tool()
def get_conversation_state() -> Dict[str, Any]:
    """
    Get the current conversation state including data product and policy pack information.
    
    Returns:
        Current conversation state
    """
    return {
        "data_product": conversation_state.get("data_product", {}),
        "policy_pack": conversation_state.get("policy_pack", {}),
        "history": conversation_state.get("history", []),
        "agents_available": list(agents.keys()),
        "current_session": current_session_id
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
        "policy_pack": {},
        "history": []
    }
    
    # Save the reset state if we have a current session
    if current_session_id:
        save_session_state(current_session_id, conversation_state)
    
    return {
        "message": "Conversation state reset successfully",
        "agents_available": list(agents.keys()),
        "current_session": current_session_id
    }

@mcp.tool()
async def route_message(message: str) -> Dict[str, Any]:
    """
    Route a message to the most appropriate agent based on content analysis.
    
    Args:
        message: User message to route
        
    Returns:
        Agent response from the most appropriate agent
    """
    try:
        # Simple keyword-based routing for basic agent selection
        message_lower = message.lower()
        
        # Define routing rules with natural language patterns
        routing_rules = [
            # Scoping agent - data product basic information
            (["name", "domain", "owner", "purpose", "upstream", "source", "data source", "input source", "where data comes from"], "scoping"),
            
            # Schema contract agent - data structure and fields
            (["field", "fields", "schema", "output", "type", "column", "data type", "structure", "table", "format"], "schema_contract"),
            
            # Policy agent - governance and access control
            (["sla", "allow", "deny", "mask", "gate", "policy", "policies", "access", "permission", "security", "governance"], "policy"),
            
            # Provisioning agent - infrastructure and deployment
            (["deploy", "infra", "infrastructure", "terraform", "provision", "environment", "kubernetes", "docker", "cloud"], "provisioning"),
            
            # Documentation agent - docs and guides
            (["doc", "documentation", "readme", "guide", "manual", "help", "explain", "describe"], "docs"),
            
            # Catalog agent - metadata and cataloging
            (["catalog", "metadata", "lineage", "dictionary", "glossary", "discovery", "search"], "catalog"),
            
            # Observability agent - monitoring and alerting
            (["monitor", "alert", "observability", "slo", "sla", "metrics", "dashboard", "tracking", "watch"], "observability")
        ]
        
        # Find matching agent based on natural language patterns
        selected_agent = "scoping"  # default
        best_match_score = 0
        
        for patterns, agent_name in routing_rules:
            score = 0
            for pattern in patterns:
                if pattern in message_lower:
                    score += 1
            if score > best_match_score:
                best_match_score = score
                selected_agent = agent_name
        
        # Check if agent is available
        if selected_agent not in agents:
            return {
                "agent": selected_agent,
                "error": "Agent not initialized - OPENAI_API_KEY required",
                "response": f"Please set OPENAI_API_KEY environment variable to use the {selected_agent} agent",
                "confidence": 0.0,
                "routing_reason": f"Message matched patterns for {selected_agent} agent",
                "current_state": conversation_state
            }
        
        # Call the selected agent - let the agent handle all the logic
        agent = agents[selected_agent]
        msg = Message("user", message)
        
        # The agent will handle conversation state, context, and all logic
        result = await agent.handle_async(conversation_state, msg)
        
        # Update conversation state
        conversation_state["history"].append({"role": "user", "content": message})
        conversation_state["history"].append({"role": "assistant", "content": result["reply"]})
        
        # Save session state if we have a current session
        if current_session_id:
            save_session_state(current_session_id, conversation_state)
        
        return {
            "agent": selected_agent,
            "response": result["reply"],
            "confidence": result["confidence"],
            "next_action": result["next_action"],
            "metadata": result["metadata"],
            "routing_reason": f"Message routed to {selected_agent} agent (score: {best_match_score})",
            "current_state": conversation_state
        }
    except Exception as e:
        # Preserve conversation state even when there's an error
        # Add the user message to history even if processing failed
        conversation_state["history"].append({"role": "user", "content": message})
        
        # Create a helpful error response that maintains context
        error_response = f"I encountered an issue processing your message: {str(e)}. Let me try to help you continue from where we left off."
        
        # Add the error response to history
        conversation_state["history"].append({"role": "assistant", "content": error_response})
        
        # Save session state if we have a current session
        if current_session_id:
            save_session_state(current_session_id, conversation_state)
        
        return {
            "agent": "routing",
            "error": str(e),
            "response": error_response,
            "confidence": 0.0,
            "next_action": "retry",
            "metadata": {"error": str(e), "state_preserved": True},
            "current_state": conversation_state
        }

@mcp.tool()
def create_session() -> Dict[str, Any]:
    """
    Create a new session and return the session ID.
    
    Returns:
        Session information including session ID
    """
    global current_session_id, conversation_state
    
    # Generate new session ID
    session_id = generate_session_id()
    current_session_id = session_id
    
    # Initialize fresh conversation state
    conversation_state = {
        "data_product": {},
        "policy_pack": {},
        "history": []
    }
    
    # Save initial state
    save_session_state(session_id, conversation_state)
    
    return {
        "session_id": session_id,
        "message": f"New session created with ID: {session_id}",
        "state": conversation_state
    }

@mcp.tool()
def load_session(session_id: str) -> Dict[str, Any]:
    """
    Load an existing session by session ID.
    
    Args:
        session_id: The session ID to load
        
    Returns:
        Session information and state
    """
    global current_session_id, conversation_state
    
    # Load session state from file
    state = load_session_state(session_id)
    
    if state is None:
        return {
            "error": f"Session {session_id} not found",
            "available_sessions": list_sessions()
        }
    
    # Update global state
    current_session_id = session_id
    conversation_state = state
    
    return {
        "session_id": session_id,
        "message": f"Session {session_id} loaded successfully",
        "state": conversation_state
    }

@mcp.tool()
def list_sessions() -> Dict[str, Any]:
    """
    List all available sessions.
    
    Returns:
        List of all sessions with metadata
    """
    sessions = list_sessions()
    
    return {
        "sessions": sessions,
        "count": len(sessions),
        "current_session": current_session_id
    }

@mcp.tool()
def delete_session(session_id: str) -> Dict[str, Any]:
    """
    Delete a session by session ID.
    
    Args:
        session_id: The session ID to delete
        
    Returns:
        Deletion confirmation
    """
    global current_session_id
    
    success = delete_session(session_id)
    
    if success:
        # If we deleted the current session, clear it
        if current_session_id == session_id:
            current_session_id = None
        
        return {
            "message": f"Session {session_id} deleted successfully",
            "deleted": True
        }
    else:
        return {
            "error": f"Failed to delete session {session_id}",
            "deleted": False
        }

@mcp.tool()
def get_current_session() -> Dict[str, Any]:
    """
    Get information about the current session.
    
    Returns:
        Current session information
    """
    if current_session_id is None:
        return {
            "current_session": None,
            "message": "No active session. Use create_session() to start a new session."
        }
    
    return {
        "current_session": current_session_id,
        "state": conversation_state,
        "session_file": get_session_filename(current_session_id)
    }

if __name__ == "__main__":
    mcp.run(transport='stdio')
