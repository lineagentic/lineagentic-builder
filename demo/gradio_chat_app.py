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
            
            logger.info("Message processed successfully")
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
        
        gr.Markdown("""
        # 🤖 Agentic Orchestrator Chat
        
        Welcome to the Data Product Creation Assistant! This AI-powered tool helps you create comprehensive data products through intelligent orchestration of specialized agents.
        
        ## 🎯 What can I help you with?
        
        **Data Product Scoping:**
        - Define product name, domain, owner, purpose
        - Identify upstream data sources
        - Set business requirements
        
        **Schema & Contracts:**
        - Define data structure and fields
        - Set up output interfaces
        - Configure SLAs and quality gates
        
        **Governance & Policies:**
        - Set access controls and permissions
        - Configure data masking rules
        - Define retention policies
        
        **Infrastructure & Deployment:**
        - Plan infrastructure requirements
        - Generate deployment configurations
        - Set up monitoring and observability
        
        ## 💡 Example Messages:
        
        - "I want to create a customer360 data product"
        - "name: customer360"
        - "domain: sales"
        - "field:name=customer_id,type=string,pk=true"
        - "allow:role:sales-manager,role:marketing-analyst"
        - "What's the current status of my data product?"
        """)
        
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
                    reset_btn = gr.Button("Reset Conversation", variant="secondary")
                    state_btn = gr.Button("Show Current State", variant="secondary")
            
            with gr.Column(scale=1):
                # Status and controls
                status_box = gr.Textbox(
                    label="Status",
                    value="Initializing...",
                    interactive=False,
                    lines=3
                )
                
                gr.Markdown("### Quick Actions")
                
                quick_actions = gr.Dropdown(
                    choices=[
                        "Get conversation state",
                        "Reset conversation",
                        "Start new data product",
                        "Define schema",
                        "Set policies",
                        "Plan infrastructure"
                    ],
                    label="Quick Actions",
                    value="Get conversation state"
                )
                
                quick_action_btn = gr.Button("Execute Quick Action", variant="secondary")
                
                # Example messages
                gr.Markdown("### 💡 Example Messages")
                
                example_messages = [
                    "I want to create a customer360 data product",
                    "name: customer360",
                    "domain: sales",
                    "owner: data-team",
                    "purpose: Provide comprehensive customer insights",
                    "field:name=customer_id,type=string,pk=true",
                    "allow:role:sales-manager",
                    "What's the current status?"
                ]
                
                for i, example in enumerate(example_messages):
                    gr.Button(
                        example,
                        variant="outline",
                        size="sm"
                    ).click(
                        lambda x=example: x,
                        outputs=msg
                    )
        
        # Event handlers
        async def send_message(message, history):
            if not message.strip():
                return history, "Please enter a message"
            
            # Initialize if not already done
            if not app.initialized:
                success = await app.initialize()
                if not success:
                    return history, "Failed to initialize agent"
            
            # Process message
            new_history, status = await app.chat_with_agent(message, history)
            return new_history, status
        
        async def clear_chat():
            return [], "Chat cleared"
        
        async def reset_conversation():
            if app.initialized:
                result = await app.reset_conversation()
                return [], f"Conversation reset: {result}"
            return [], "Agent not initialized"
        
        async def show_state():
            if app.initialized:
                state = await app.get_conversation_state()
                return [], f"Current state: {state}"
            return [], "Agent not initialized"
        
        async def execute_quick_action(action):
            if not app.initialized:
                return [], "Agent not initialized"
            
            if action == "Get conversation state":
                state = await app.get_conversation_state()
                return [], f"Current state: {state}"
            elif action == "Reset conversation":
                result = await app.reset_conversation()
                return [], f"Conversation reset: {result}"
            elif action == "Start new data product":
                return [], "Ready to start new data product. Try: 'I want to create a new data product'"
            elif action == "Define schema":
                return [], "Ready to define schema. Try: 'field:name=id,type=string,pk=true'"
            elif action == "Set policies":
                return [], "Ready to set policies. Try: 'allow:role:analyst'"
            elif action == "Plan infrastructure":
                return [], "Ready to plan infrastructure. Try: 'deploy:environment=production'"
            else:
                return [], f"Unknown action: {action}"
        
        # Connect event handlers
        send_btn.click(
            send_message,
            inputs=[msg, chatbot],
            outputs=[chatbot, status_box]
        )
        
        msg.submit(
            send_message,
            inputs=[msg, chatbot],
            outputs=[chatbot, status_box]
        )
        
        clear_btn.click(
            clear_chat,
            outputs=[chatbot, status_box]
        )
        
        reset_btn.click(
            reset_conversation,
            outputs=[chatbot, status_box]
        )
        
        state_btn.click(
            show_state,
            outputs=[chatbot, status_box]
        )
        
        quick_action_btn.click(
            execute_quick_action,
            inputs=[quick_actions],
            outputs=[chatbot, status_box]
        )
        
        # Initialize on load
        async def initialize_on_load():
            success = await app.initialize()
            if success:
                return "Ready to chat! 🚀"
            else:
                return "Failed to initialize. Please check your configuration."
        
        interface.load(
            initialize_on_load,
            outputs=[status_box]
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
