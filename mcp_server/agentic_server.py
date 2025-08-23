"""
MCP Server that exposes agentic orchestration agents as tools.
This server provides access to all the structured agents for data product creation.
"""
import logging
import sys
import os
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

mcp = FastMCP("agentic_orchestration_server")

# Global state to maintain conversation context
conversation_state = {
    "data_product": {},
    "policy_pack": {},
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
    Get the current conversation state and data product specification.
    
    Returns:
        Current conversation state including data product and policy pack
    """
    return {
        "data_product": conversation_state.get("data_product", {}),
        "policy_pack": conversation_state.get("policy_pack", {}),
        "history": conversation_state.get("history", []),
        "agents_available": list(agents.keys())
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
    return {
        "message": "Conversation state reset successfully",
        "agents_available": list(agents.keys())
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
        # Simple keyword-based routing
        message_lower = message.lower()
        
        # Define routing rules
        routing_rules = [
            (["name:", "domain:", "owner:", "purpose:", "upstreams:"], "scoping"),
            (["field:", "fields:", "schema:", "output:", "type:"], "schema_contract"),
            (["sla:", "allow:", "mask:", "gate:", "policies:"], "policy"),
            (["deploy:", "infra:", "terraform:", "provision:"], "provisioning"),
            (["doc:", "documentation:", "readme:"], "docs"),
            (["catalog:", "metadata:", "lineage:"], "catalog"),
            (["monitor:", "alert:", "observability:", "slo:"], "observability")
        ]
        
        # Find matching agent
        selected_agent = "scoping"  # default
        for keywords, agent_name in routing_rules:
            if any(keyword in message_lower for keyword in keywords):
                selected_agent = agent_name
                break
        
        # Check if agent is available
        if selected_agent not in agents:
            return {
                "agent": selected_agent,
                "error": "Agent not initialized - OPENAI_API_KEY required",
                "response": f"Please set OPENAI_API_KEY environment variable to use the {selected_agent} agent",
                "confidence": 0.0,
                "routing_reason": f"Message matched keywords for {selected_agent} agent"
            }
        
        # Call the selected agent
        agent = agents[selected_agent]
        msg = Message("user", message)
        result = await agent.handle_async(conversation_state, msg)
        
        # Update conversation state
        conversation_state["history"].append({"role": "user", "content": message})
        conversation_state["history"].append({"role": "assistant", "content": result["reply"]})
        
        return {
            "agent": selected_agent,
            "response": result["reply"],
            "confidence": result["confidence"],
            "next_action": result["next_action"],
            "metadata": result["metadata"],
            "routing_reason": f"Message matched keywords for {selected_agent} agent",
            "current_state": conversation_state
        }
    except Exception as e:
        return {
            "agent": "routing",
            "error": str(e),
            "response": f"Error in message routing: {str(e)}",
            "confidence": 0.0
        }

if __name__ == "__main__":
    mcp.run(transport='stdio')
