"""
DP Builder Agent that uses dp_server.py as MCP server for comprehensive data product analysis.
"""
import logging
import asyncio
import os
from typing import Dict, Any, Optional
from contextlib import AsyncExitStack
from agents import Agent, Runner
from agents.mcp.server import MCPServerStdio
from dp_composer_server.mcp_params import dp_composer_mcp_server_params
from dp_chat_agent.utils.session_utils import save_conversation_state, load_conversation_state, create_new_session
from dp_chat_agent.utils.file_utils import dump_json_record
from dp_chat_agent.utils.model_manager import get_model
from dp_chat_agent.utils.response_parser import ResponseParser

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
    - ** IMPORTANT: Always guide the user to provide the next required information with clear examples.

    **IMPORTANT - TOOL OUTPUT PRESERVATION:**
    When you call a tool, the tool will return structured data including:
    - reply: The response message
    - extracted_data: Any data extracted from the user input
    - confidence: Confidence level
    - next_action: Suggested next action
    - metadata: Additional metadata
    - missing_fields: List of missing required fields
    
    **YOU MUST PRESERVE THIS STRUCTURED DATA IN YOUR FINAL RESPONSE.**
    After calling a tool, respond with the tool's reply message, but also ensure that any extracted_data, confidence, next_action, metadata, and missing_fields from the tool are preserved and accessible.

    **FORBIDDEN ACTIONS:**
    - Calling the same tool multiple times for the same user input
    - Responding without calling the appropriate tool first
    - Asking for multiple fields at once
    - Making assumptions about what the user wants
    - Skipping required tool calls
    - Losing the structured data from tool outputs
    
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
                    for params in dp_composer_mcp_server_params
                ]
                
                # Create agent with the MCP servers
                dp_composer_agent = await self.create_agent(dp_mcp_servers)
                
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
                result = await Runner.run(dp_composer_agent, messages_string, max_turns=60)  
                
                # Get the final output from the result
                final_output = result.final_output if hasattr(result, 'final_output') else str(result)
                logging.info(f"final_output------------------: {str(final_output)}")
                
                # Parse the agent response using the ResponseParser
                parser = ResponseParser(model_name="gpt-4o-mini")
                parsed_data = parser.parse_agent_response(str(final_output))
                # Extract parsed data
                reply = parsed_data.get_reply()
                extracted_data = parsed_data.extracted_data
                confidence = parsed_data.confidence
                next_action = parsed_data.next_action
                metadata = parsed_data.metadata
                missing_fields = parsed_data.missing_fields
                

                
                conversation_state["history"].append({"role": "user", "content": user_message})
                conversation_state["history"].append({"role": "assistant", "content": reply})
                
                # Handle extracted data if present
                if extracted_data:
                    data_product = conversation_state.get("data_product", {})
                    for key, value in extracted_data.items():
                        if value:
                            data_product[key] = value
                    conversation_state["data_product"] = data_product

                save_conversation_state(conversation_state, self.session_id)

                # Return the result with all parsed structured data
                return_result = {
                    "final_output": final_output,
                    "reply": reply,
                    "extracted_data": extracted_data,
                    "confidence": confidence,
                    "next_action": next_action,
                    "metadata": metadata,
                    "missing_fields": missing_fields
                }
                return dump_json_record(self.agent_name, return_result)
                
        except Exception as e:
            logger.error(f"Error in run_with_session: {e}")
            return {"error": f"Agent execution failed: {str(e)}"}
            

    async def run(self, current_message: str = None):
        try:
            logger.info(f"Starting data product analysis for {self.agent_name}")
            result = await self.run_with_session(current_message)
            logger.info(f"Completed data product analysis for {self.agent_name}")
            return result
        except Exception as e:
            logger.error(f"Error running {self.agent_name}: {e}")
            return {"error": str(e)}
      


# Factory function
def create_dp_composer_agent(agent_name: str, user_message: str, model_name: str = "gpt-4o-mini", session_id: str = None) -> DPBuilderAgent:
    """Factory function to create a DPBuilderAgent instance"""
    return DPBuilderAgent(agent_name=agent_name, user_message=user_message, model_name=model_name, session_id=session_id)

if __name__ == "__main__":
    # Example usage
    async def main():
        agent = create_dp_composer_agent("test_agent", "Hello, I want to create a data product for customer analytics")
        result = await agent.run()
        print(result)
    
    asyncio.run(main())
