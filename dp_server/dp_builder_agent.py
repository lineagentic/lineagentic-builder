"""
DP Builder Agent that uses dp_server.py as MCP server for comprehensive data product analysis.
"""
import logging
import asyncio
from typing import Dict, Any, Optional
from contextlib import AsyncExitStack
from agents import Agent, Tool, Runner, trace
from agents.mcp.server import MCPServerStdio
from mcp_params import dp_builder_mcp_server_params
from file_utils import dump_json_record
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def comprehensive_analysis_instructions(name: str):
    return f"""
    You are the {name} data product builder agent.
    
    **CRITICAL: YOU MUST CALL TOOLS IN THIS EXACT SEQUENCE BEFORE RESPONDING.**
    
    **AVAILABLE TOOLS:**
    1. create_session() - Create a new chat session (ONLY call this if no session exists)
    2. get_conversation_state(session_id) - Get current conversation state for a session
    3. scoping_agent(user_message, session_id) - Process user message and extract information
    4. data_contract_agent(user_message, session_id) - Define data contract
    5. reset_conversation(session_id) - Reset conversation state for a session
    6. list_sessions() - List all available sessions
    
    **MANDATORY TOOL CALL SEQUENCE - NO EXCEPTIONS:**
    1. FIRST: Check if you already have a session_id from previous tool calls or memory
    2. SECOND: If you have a session_id, use it; if not, call create_session() ONCE
    3. THIRD: Call get_conversation_state(session_id) with the session ID
    4. FOURTH: Call scoping_agent(user_message, session_id) with the current user message
    5. FIFTH: Use the scoping_agent response to determine what to ask the user next
    6. ONLY THEN: Respond to the user based on the tool results
    
    **IMPORTANT SESSION RULES:**
    - NEVER call create_session() if you already have a session_id
    - ALWAYS use the same session_id for all subsequent tool calls
    - Store the session_id and reuse it for the entire conversation
    - Only create a new session if you don't have one stored
    - The session_id should persist across multiple user messages
    - If you see "session_id" in any previous tool response, use that ID
    
    **EXAMPLE CORRECT WORKFLOW:**
    User: "I want to create a data product for customer analytics"
    You MUST:
    1. Check if you have a session_id from previous interactions
    2. If no session_id: call create_session() to get a session_id
    3. Call get_conversation_state(session_id) 
    4. Call scoping_agent("I want to create a data product for customer analytics", session_id)
    5. Based on scoping_agent response, ask user for the FIRST missing field only
    
    **FORBIDDEN ACTIONS:**
    - Calling create_session() if you already have a session_id
    - Creating new sessions unnecessarily
    - Responding without calling the required tools first
    - Asking for multiple fields at once
    - Making assumptions about what the user wants
    - Skipping the scoping_agent() call
    - Not using session_id in tool calls
    
    **REMEMBER: CHECK FOR EXISTING SESSION FIRST, CREATE SESSION ONLY IF NEEDED, THEN REUSE THE SAME SESSION_ID FOR THE ENTIRE CONVERSATION.**
    """

class DPBuilderAgent:
    def __init__(self, agent_name: str, user_message: str, model_name: str = "gpt-4o-mini", get_model_func=None, session_id: str = None):
        self.agent_name = agent_name
        self.user_message = user_message
        self.model_name = model_name
        self.get_model_func = get_model_func
        self.session_id = session_id
        
    async def create_agent(self, dp_mcp_servers) -> 'Agent':
        # Use the passed get_model_func or fall back to the centralized one
        if self.get_model_func:
            model = self.get_model_func(self.model_name)
        else:
            from model_manager import get_model
            model = get_model(self.model_name)
            
        # Debug: Log the MCP servers being passed to the agent
        logger.info(f"Creating agent with {len(dp_mcp_servers)} MCP servers")
        logger.info(f"MCP servers types: {[type(server) for server in dp_mcp_servers]}")
        
        # Create agent with comprehensive instructions
        agent = Agent(
            name=self.agent_name,
            instructions=comprehensive_analysis_instructions(self.agent_name),
            model=model,
            mcp_servers=dp_mcp_servers,
            tool_use_behavior='run_llm_again',  # Allow agent to continue after tool calls
            reset_tool_choice=False,  # Don't reset tool choice
        )
        
        # Store session_id in agent's memory for persistence across runs
        if self.session_id:
            agent.memory["session_id"] = self.session_id
            logger.info(f"Agent created with existing session_id: {self.session_id}")
        else:
            logger.info("Agent created without session_id - will create new session on first run")
        
        # Debug: Log what tools the agent has access to
        logger.info(f"Agent created: {agent.name}")
        logger.info(f"Agent instructions length: {len(comprehensive_analysis_instructions(self.agent_name))}")
        
        # Debug: Check what tools the agent has access to
        try:
            mcp_tools = await agent.get_mcp_tools()
            logger.info(f"Agent MCP tools: {[tool.name for tool in mcp_tools]}")
        except Exception as e:
            logger.warning(f"Could not get MCP tools: {e}")
        
        return agent

    async def run_with_session(self, user_message: str):
        """Run the agent while maintaining conversation state through the MCP server."""
        try:
            # Use the working MCP server approach from the original code
            from agents.mcp.server import MCPServerStdio
            from contextlib import AsyncExitStack
            
            async with AsyncExitStack() as stack:
                dp_mcp_servers = [
                    await stack.enter_async_context(
                        MCPServerStdio(params, client_session_timeout_seconds=120)
                    )
                    for params in dp_builder_mcp_server_params
                ]
                
                # Debug: Log the MCP servers being created
                logger.info(f"Created {len(dp_mcp_servers)} MCP servers")
                for i, server in enumerate(dp_mcp_servers):
                    logger.info(f"MCP Server {i}: {type(server)}")
                
                # Create agent with the MCP servers
                comprehensive_agent = await self.create_agent(dp_mcp_servers)
                
                # Debug: Check what tools the agent has access to
                logger.info(f"Agent created successfully: {comprehensive_agent.name}")
                
                # Run the agent - the conversation state is maintained in dp_server.py
                result = await Runner.run(comprehensive_agent, user_message, max_turns=60)
                
                # Extract session_id from result if it's a new session
                if isinstance(result.final_output, dict):
                    # Check if the agent created a new session
                    if "session_id" in result.final_output:
                        self.session_id = result.final_output["session_id"]
                        logger.info(f"New session created: {self.session_id}")
                    elif "extracted_data" in result.final_output and "session_id" in result.final_output["extracted_data"]:
                        self.session_id = result.final_output["extracted_data"]["session_id"]
                        logger.info(f"Session ID extracted: {self.session_id}")
                
                # Return the result
                return dump_json_record(self.agent_name, result.final_output)
                
        except Exception as e:
            logger.error(f"Error in run_with_session: {e}")
            return {"error": f"Agent execution failed: {str(e)}"}

    async def run_agent(self, dp_mcp_servers, user_message: str):
        """
        Run the agent with proper orchestration between scoping and data contract phases.
        """
        try:
            comprehensive_agent = await self.create_agent(dp_mcp_servers)
            
            # Debug: Check what tools the agent has access to
            logger.info(f"Agent created successfully: {comprehensive_agent.name}")
            
            # Try to list tools from the MCP server to see what's available
            try:
                for i, server in enumerate(dp_mcp_servers):
                    logger.info(f"Checking MCP Server {i} for tools...")
                    # This might not work depending on the MCP server implementation
                    logger.info(f"Server {i} type: {type(server)}")
            except Exception as e:
                logger.warning(f"Could not inspect MCP server tools: {e}")
            
            # Increase max_turns to handle the two-phase workflow properly
            # Each phase might need multiple turns to gather all required information
            result = await Runner.run(comprehensive_agent, user_message, max_turns=60)
            
            # Return the result
            return dump_json_record(self.agent_name, result.final_output)
            
        except Exception as e:
            logger.error(f"Error in run_agent: {e}")
            return {"error": f"Agent execution failed: {str(e)}"}
            

    async def run_with_trace(self, user_message: str):
        trace_name = f"{self.agent_name}-dp-builder-agent"
        trace_id = f"{self.agent_name.lower()}-{hash(user_message) % 10000}"
        
        # Simple tracing - you can enhance this
        logger.info(f"Starting trace: {trace_name} with ID: {trace_id}")
        try:
            return await self.run_with_session(user_message)
        finally:
            logger.info(f"Completed trace: {trace_name}")

    async def run(self, current_message: str = None):
        try:
            logger.info(f"Starting data product analysis for {self.agent_name}")
            # Use current message if provided, otherwise fall back to initialization message
            result = await self.run_with_trace(current_message)
            logger.info(f"Completed data product analysis for {self.agent_name}")
            return result
        except Exception as e:
            logger.error(f"Error running {self.agent_name}: {e}")
            return {"error": str(e)}
      
    def get_session_id(self) -> str:
        """Get the current session ID."""
        return self.session_id
    
    def set_session_id(self, session_id: str):
        """Set the session ID."""
        self.session_id = session_id
    
    def has_active_session(self) -> bool:
        """Check if the agent has an active session."""
        return self.session_id is not None
    
    def get_session_status(self) -> dict:
        """Get comprehensive session status information."""
        return {
            "has_session": self.has_active_session(),
            "session_id": self.session_id,
            "agent_name": self.agent_name
        }

# Factory function
def create_dp_builder_agent(agent_name: str, user_message: str, model_name: str = "gpt-4o-mini", get_model_func=None, session_id: str = None) -> DPBuilderAgent:
    """Factory function to create a DPBuilderAgent instance"""
    return DPBuilderAgent(agent_name=agent_name, user_message=user_message, model_name=model_name, get_model_func=get_model_func, session_id=session_id)

if __name__ == "__main__":
    # Example usage
    async def main():
        agent = create_dp_builder_agent("test_agent", "Hello, I want to create a data product for customer analytics")
        result = await agent.run()
        print(result)
    
    asyncio.run(main())
