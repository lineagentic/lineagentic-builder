"""
DP Builder Agent that uses dp_server.py as MCP server for comprehensive data product analysis.
"""
import logging
import asyncio
from typing import Dict, Any, Optional
from contextlib import AsyncExitStack
from agents import Agent, Tool, Runner, trace
from agents.mcp.server import MCPServerStdio
from dp_server.mcp_params import dp_builder_mcp_server_params
from dp_server.session_utils import save_conversation_state
from dp_server.session_utils import load_conversation_state
from dp_server.session_utils import create_new_session
from dp_server.file_utils import dump_json_record
from dp_server.model_manager import get_model

# Configure logging with console output
# Only configure if not already configured
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # This ensures output goes to console
            logging.FileHandler('dp_builder.log')  # Optional: also log to file
        ]
    )
logger = logging.getLogger(__name__)

def comprehensive_analysis_instructions(name: str):
    return f"""
    You are the {name} data product builder agent.
    
    **CRITICAL: CALL TOOLS ONLY ONCE PER USER MESSAGE - NO REDUNDANT CALLS**
    
    **MESSAGE FORMAT:**
    You will receive a formatted string containing:
    - User Message: [the actual user message]
    - Conversation State: [the current conversation state as a dictionary]
    
    **AVAILABLE TOOLS:**
    1. scoping_agent(messages) - Process user message and extract information (pass the entire formatted string)
    2. data_contract_agent(messages) - Define data contract (pass the entire formatted string)

    **TOOL CALL STRATEGY - CALL EACH TOOL ONLY ONCE PER USER MESSAGE:**
    1. **FIRST**: Check conversation state to see what stage we're in
    2. **IF SCOPING INCOMPLETE**: Call scoping_agent(messages) ONCE with the entire formatted input string
    3. **IF SCOPING COMPLETE**: Call data_contract_agent(messages) ONCE with the entire formatted input string
    4. **NEVER**: Call the same tool multiple times for the same user message
    5. **RESPOND**: Based on the tool response, ask the user for the next required information

    **CONVERSATION FLOW:**
    - Start with scoping_agent to gather basic information (name, purpose, etc.)
    - Once scoping is complete, move to data_contract_agent for detailed field definitions
    - Each tool call should advance the conversation to the next logical step

    **FORBIDDEN ACTIONS:**
    - Calling the same tool multiple times for the same user input
    - Responding without calling the appropriate tool first
    - Asking for multiple fields at once
    - Making assumptions about what the user wants
    - Skipping required tool calls
    
    """
      
class DPBuilderAgent:
    def __init__(self, agent_name: str, user_message: str, model_name: str = "gpt-4o-mini", session_id: str = None):
        self.agent_name = agent_name
        self.user_message = user_message
        self.model_name = model_name
        self.session_id = session_id

        
    async def create_agent(self, dp_mcp_servers) -> 'Agent':

        
        model = get_model(self.model_name)
        
        # Create agent with comprehensive instructions
        agent = Agent(
            name=self.agent_name,
            instructions=comprehensive_analysis_instructions(self.agent_name),
            model=model,
            mcp_servers=dp_mcp_servers,
            tool_use_behavior='run_llm_again',  # Allow agent to continue after tool calls
            reset_tool_choice=False,  # Don't reset tool choice
        )
       
        return agent

    async def run_with_session(self, user_message: str):
        """Run the agent while maintaining conversation state through the MCP server."""
        try:
            # Use the working MCP server approach from the original code
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
                dp_builder_agent = await self.create_agent(dp_mcp_servers)
                
                # Debug: Check what tools the agent has access to
                logger.info(f"Agent created successfully: {dp_builder_agent.name}")
                
                # Load or create conversation state
                if self.session_id:
                    conversation_state = load_conversation_state(self.session_id)
                else:
                    self.session_id = create_new_session()
                    conversation_state = load_conversation_state(self.session_id)
                
                # Run the agent - pass both user_message and conversation_state as a formatted string
                messages_string = f"""
                User Message: {user_message}
                
                Conversation State: {conversation_state}
                """
                result = await Runner.run(dp_builder_agent, messages_string, max_turns=60)  
                # Extract session_id from result if it's a new session
                
                # Get the final output from the result
                final_output = result.final_output if hasattr(result, 'final_output') else str(result)
                
                # Extract reply and extracted_data from final_output
                reply = str(final_output)  # Default to string representation
                extracted_data = {}
                logging.info(f"Final output------------------: {str(final_output)}")
                # Check if final_output is a dict and contains the expected fields
                if isinstance(final_output, dict):
                    reply = final_output.get("reply", str(final_output))
                    extracted_data = final_output.get("extracted_data", {})
                    logging.info(f"extracted_data------------------: {str(extracted_data)}")
                elif hasattr(final_output, 'reply'):
                    reply = final_output.reply
                    extracted_data = getattr(final_output, 'extracted_data', {})
                    logging.info(f"extracted_data------------------: {str(extracted_data)}")
                conversation_state["history"].append({"role": "user", "content": user_message})
                conversation_state["history"].append({"role": "assistant", "content": reply})
                
                # Handle extracted data if present
                if extracted_data:
                    data_product = conversation_state.get("data_product", {})
                    logging.info(f"Updating conversation state with extracted data: {extracted_data}")
                    for key, value in extracted_data.items():
                        if value:
                            data_product[key] = value
                    conversation_state["data_product"] = data_product
                    logging.info(f"Updated conversation state: {conversation_state}")
                else:
                    logging.info(f"No extracted data in result: {final_output}")               

                
                save_conversation_state(conversation_state, self.session_id)

                # Return the result
                return dump_json_record(self.agent_name, final_output)
                
        except Exception as e:
            logger.error(f"Error in run_with_session: {e}")
            return {"error": f"Agent execution failed: {str(e)}"}
            

    async def run_with_trace(self, user_message: str):
        trace_name = f"{self.agent_name}-agent"
        trace_id = f"{self.agent_name.lower()}-{hash(user_message) % 10000}"
        
        # Simple tracing - you can enhance this
        logger.info(f"Starting trace: {trace_name} with ID: {trace_id}")
        try:
            return await self.run_with_session(user_message)
        except Exception as e:
            logger.error(f"Error in run_with_trace: {e}")
            return {"error": f"Agent execution failed: {str(e)}"}


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
      


# Factory function
def create_dp_builder_agent(agent_name: str, user_message: str, model_name: str = "gpt-4o-mini", session_id: str = None) -> DPBuilderAgent:
    """Factory function to create a DPBuilderAgent instance"""
    return DPBuilderAgent(agent_name=agent_name, user_message=user_message, model_name=model_name, session_id=session_id)

if __name__ == "__main__":
    # Example usage
    async def main():
        agent = create_dp_builder_agent("test_agent", "Hello, I want to create a data product for customer analytics")
        result = await agent.run()
        print(result)
    
    asyncio.run(main())
