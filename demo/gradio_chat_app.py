"""
Gradio Chat App for Agentic Orchestrator
A web interface for chatting with the data product creation agentic orchestrator.
"""

import gradio as gr
import asyncio
import logging
from typing import List, Tuple, Optional
import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from agents import Agent, Tool, Runner, trace
from agents.mcp.server import MCPServerStdio
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import shared modules
from mcp_server.mcp_params import agentic_mcp_server_params
from mcp_server.agentic_instructions import comprehensive_agentic_instructions

# Get instructions for the agentic orchestrator
instructions = comprehensive_agentic_instructions("data product agentic orchestration")

class AgenticChatApp:
    """Gradio chat application for agentic orchestrator"""
    
    def __init__(self):
        self.mcp_server = None
        self.agent = None
        self.initialized = False
        
    async def initialize(self):
        """Initialize the MCP server and agent"""
        try:
            logger.info("Initializing MCP server and agent...")
            
            # Check if OpenAI API key is available
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.error("OPENAI_API_KEY not found in environment variables")
                return False
            else:
                logger.info("OpenAI API key found and loaded")
            
            # Initialize MCP server
            self.mcp_server = MCPServerStdio(agentic_mcp_server_params[0], client_session_timeout_seconds=120)
            await self.mcp_server.__aenter__()
            
            # Create agent
            self.agent = Agent(
                name="agentic_orchestrator",
                instructions=instructions,
                model="gpt-4o-mini",
                mcp_servers=[self.mcp_server],
            )
            
            self.initialized = True
            logger.info("Agentic orchestrator initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing agentic orchestrator: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.mcp_server:
            try:
                await self.mcp_server.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error cleaning up MCP server: {e}")
    
    async def chat_with_agent(self, message: str, history: List[List[str]]) -> Tuple[List[List[str]], str]:
        """
        Chat with the agentic orchestrator
        
        Args:
            message: User message
            history: Chat history
            
        Returns:
            Updated chat history and status message
        """
        if not self.initialized:
            return history, "Error: Agent not initialized. Please try again."
        
        try:
            logger.info(f"Processing message: {message[:50]}...")
            
            # Run the agent with the message
            with trace("agentic_orchestrator"):
                result = await Runner.run(self.agent, message, max_turns=30)
            
            # Get the response
            response = result.final_output
            
            # Update history
            history.append([message, response])
            
            logger.info(f"Message processed successfully. Response: {response[:100]}...")
            logger.info(f"History length after update: {len(history)}")
            return history, "Success"
            
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            logger.error(error_msg)
            history.append([message, f"Error: {error_msg}"])
            return history, f"Error: {error_msg}"
    
    async def get_conversation_state(self) -> str:
        """Get current conversation state"""
        if not self.initialized:
            return "Agent not initialized"
        
        try:
            result = await self.mcp_server.call_tool("get_conversation_state", {})
            
            # Handle MCP response format - result should be a dictionary
            if hasattr(result, 'content') and result.content:
                # If it's a structured response, extract the content
                if hasattr(result.content[0], 'text'):
                    return result.content[0].text
                else:
                    return str(result.content[0])
            elif isinstance(result, dict):
                # If it's already a dictionary, convert to JSON
                import json
                return json.dumps(result, indent=2)
            else:
                # Fallback to string representation
                return str(result)
        except Exception as e:
            return f"Error getting conversation state: {str(e)}"
    
    async def reset_conversation(self) -> str:
        """Reset the conversation"""
        if not self.initialized:
            return "Agent not initialized"
        
        try:
            result = await self.mcp_server.call_tool("reset_conversation", {})
            return str(result)
        except Exception as e:
            return f"Error resetting conversation: {str(e)}"

# Global app instance
app = AgenticChatApp()

def create_chat_interface():
    """Create the Gradio chat interface"""
    
    with gr.Blocks(
        title="Agentic Orchestrator Chat",
        theme=gr.themes.Soft(),
        css="""
        .gradio-container {
            max-width: 1200px !important;
        }
        .chat-message {
            padding: 10px;
            border-radius: 8px;
            margin: 5px 0;
        }
        .user-message {
            background-color: #e3f2fd;
            border-left: 4px solid #2196f3;
        }
        .bot-message {
            background-color: #f3e5f5;
            border-left: 4px solid #9c27b0;
        }
        """
    ) as interface:
        

        
        with gr.Row():
            with gr.Column(scale=3):
                # Chat interface
                chatbot = gr.Chatbot(
                    label="Chat with Agentic Orchestrator",
                    height=500,
                    show_label=True,
                    container=True,
                    bubble_full_width=False
                )
                
                with gr.Row():
                    msg = gr.Textbox(
                        label="Your Message",
                        placeholder="Type your message here...",
                        lines=2,
                        scale=4
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)
                
                with gr.Row():
                    clear_btn = gr.Button("Clear Chat", variant="secondary")
                    state_btn = gr.Button("Show Current State", variant="secondary")
            
            with gr.Column(scale=1):
                # State display box
                state_display = gr.Markdown(
                    value="📊 **Data Product State**\n\nNo data product being built yet.",
                    label="Current State",
                    height=500
                )
            
        # Event handlers
        async def send_message(message, history):
            if not message.strip():
                return history
            
            # Initialize if not already done
            if not app.initialized:
                success = await app.initialize()
                if not success:
                    history.append([message, "Failed to initialize agent"])
                    return history
            
            try:
                # Process message with the agent
                new_history, status = await app.chat_with_agent(message, history)
                
                # Ensure the history is properly updated
                if new_history and len(new_history) > 0:
                    # The last message should be the user's message and agent's response
                    last_message = new_history[-1]
                    if len(last_message) == 2 and last_message[0] == message:
                        # History is properly formatted, return it
                        return new_history
                    else:
                        # Something went wrong with the history format
                        logger.warning(f"Unexpected history format: {last_message}")
                        return new_history
                else:
                    # No history returned, create a basic response
                    history.append([message, "No response received from agent"])
                    return history
                    
            except Exception as e:
                logger.error(f"Error in send_message: {e}")
                history.append([message, f"Error: {str(e)}"])
                return history
        
        async def clear_chat():
            return []
        

        
        async def show_state():
            if app.initialized:
                try:
                    state = await app.get_conversation_state()
                    
                    # The state should now be a proper JSON string from the MCP response
                    import json
                    
                    try:
                        # Parse the JSON directly
                        data = json.loads(state)
                        
                        # Extract data_product and policy_pack sections, and include schema information
                        data_product = data.get("data_product", {})
                        policy_pack = data.get("policy_pack", {})
                        
                        # Create a comprehensive display that includes schema information
                        display_data = {
                            "data_product": {
                                "name": data_product.get("name"),
                                "domain": data_product.get("domain"),
                                "owner": data_product.get("owner"),
                                "purpose": data_product.get("purpose"),
                                "upstreams": data_product.get("upstreams", []),
                                "interfaces": data_product.get("interfaces", {}),
                                "schema": data_product.get("schema", []),
                                "outputs": data_product.get("outputs", [])
                            },
                            "policy_pack": policy_pack
                        }
                        
                        # Format as pretty JSON
                        pretty_json = json.dumps(display_data, indent=2)
                        state_message = f"📊 **Data Product State**\n\n```json\n{pretty_json}\n```"
                        return state_message
                    except json.JSONDecodeError as e:
                        # If JSON parsing fails, show the raw state for debugging
                        return f"❌ **Error parsing JSON:** {str(e)}\n\nRaw state: {state[:200]}..."
                        
                except Exception as e:
                    error_message = f"❌ **Error getting state:** {str(e)}"
                    return error_message
            else:
                return "❌ **Agent not initialized**"
        

        
        # Connect event handlers
        send_btn.click(
            send_message,
            inputs=[msg, chatbot],
            outputs=[chatbot]
        )
        
        msg.submit(
            send_message,
            inputs=[msg, chatbot],
            outputs=[chatbot]
        )
        
        clear_btn.click(
            clear_chat,
            outputs=[chatbot]
        )
        

        
        state_btn.click(
            show_state,
            outputs=[state_display]
        )
        

        

        
        # Cleanup on close
        interface.unload(
            app.cleanup
        )
    
    return interface

def main():
    """Main function to run the Gradio app"""
    print("🚀 Starting Agentic Orchestrator Chat App...")
    
    # Create the interface
    interface = create_chat_interface()
    
    # Launch the app
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        debug=True,
        show_error=True
    )

if __name__ == "__main__":
    main()
