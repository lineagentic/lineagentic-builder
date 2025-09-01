import os
import sys
import logging
from contextlib import AsyncExitStack
from agents import Agent, Tool, Runner, trace
from agents.mcp.server import MCPServerStdio
from typing import Dict, Any, Optional

# Get logger for this module
logger = logging.getLogger(__name__)

MAX_TURNS = 20  # Reasonable limit for data product scoping


class DataProductScopingAgent:
    """Agent for data product scoping and definition"""
    
    def __init__(self, agent_name: str, user_requirements: str, model_name: str = "gpt-4o-mini", get_model_func=None):
        self.agent_name = agent_name
        self.model_name = model_name
        self.user_requirements = user_requirements
        self.get_model_func = get_model_func

    async def create_agent(self, dp_mcp_servers) -> Agent:
        # Use the passed get_model_func or let the agents library handle the model
        if self.get_model_func:
            model = self.get_model_func(self.model_name)
            agent = Agent(
                name=self.agent_name,
                instructions=self._get_instructions(),
                model=model,
                mcp_servers=dp_mcp_servers,
            )
        else:
            # Let the agents library handle the model automatically
            # It will use the OPENAI_API_KEY environment variable
            agent = Agent(
                name=self.agent_name,
                instructions=self._get_instructions(),
                mcp_servers=dp_mcp_servers,
            )
            logger.info(f"Using default model configuration for {self.model_name}")
            
        return agent

    def _get_instructions(self) -> str:
        """Get the agent instructions"""
        return f"""
        You are the {self.agent_name} data product scoping agent.
        
        **Your Task:** Perform complete data product scoping in a single comprehensive process.
        
        **Complete Scoping Process:**
        
        **Step 1: Initial Scoping Analysis**
        1. Call the scoping_agent() MCP tool with the user's requirements
        2. Follow the tool's instructions to analyze and extract data product information
        3. Store the initial scoping results for iterative refinement
        
        **Step 2: Iterative Refinement**
        1. Based on the initial results, identify any missing or unclear information
        2. Call the scoping_agent() MCP tool again with clarifying questions or additional details
        3. Continue this process until all required fields are complete
        
        **Step 3: Validation and Confirmation**
        1. Call get_conversation_state() to review the current data product state
        2. Verify that all required fields are properly defined
        3. If any gaps remain, continue with additional scoping_agent() calls
        
        **Step 4: Final Documentation**
        1. Once scoping is complete, provide a comprehensive summary of the data product
        2. Include all extracted information in a well-structured format
        3. Provide recommendations for next steps in the data product development process
        
        **Required Data Product Fields:**
        - name: The name of the data product
        - domain: The business domain or area
        - owner: The person or team responsible
        - purpose: The business purpose and value proposition
        - upstreams: Data sources and dependencies
        
        **Important Guidelines:**
        - Use the scoping_agent() MCP tool for all data product analysis
        - Follow the tool's instructions precisely for each interaction
        - Maintain context between calls - build upon previous information
        - Ensure all required fields are complete before finalizing
        - If any step fails, provide clear error information and stop the process
        - Use get_conversation_state() to track progress
        - Use reset_conversation() if you need to start fresh
        
        **Workflow Summary:**
        Initial Analysis → Iterative Refinement → Validation → Final Documentation → Complete Data Product Scope
        """

    async def run_agent(self, dp_mcp_servers, user_requirements: str):
        # Create single agent for comprehensive scoping
        scoping_agent = await self.create_agent(dp_mcp_servers)
        
        # Run the complete scoping in one go
        result = await Runner.run(scoping_agent, user_requirements, max_turns=MAX_TURNS)
        
        # Return the final output
        return result.final_output

    async def run_with_mcp_servers(self, user_requirements: str):
        async with AsyncExitStack() as stack:
            # Import the MCP server parameters
            from dp_server.mcp_params import agentic_mcp_server_params
            
            dp_mcp_servers = [
                await stack.enter_async_context(
                    MCPServerStdio(params, client_session_timeout_seconds=120)
                )
                for params in agentic_mcp_server_params
            ]
            return await self.run_agent(dp_mcp_servers, user_requirements=user_requirements)

    async def run_with_trace(self, user_requirements: str):
        trace_name = f"{self.agent_name}-scoping-agent"
        trace_id = f"trace_{self.agent_name.lower()}_{int(os.getpid())}"
        with trace(trace_name, trace_id=trace_id):
            return await self.run_with_mcp_servers(user_requirements=user_requirements)

    async def run(self):
        try:
            logger.info(f"Starting data product scoping for {self.agent_name}")
            result = await self.run_with_trace(self.user_requirements)
            logger.info(f"Completed data product scoping for {self.agent_name}")
            return result
        except Exception as e:
            logger.error(f"Error running {self.agent_name}: {e}")
            return {"error": str(e)}

