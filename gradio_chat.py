#!/usr/bin/env python3
"""
Gradio Web Interface for Data Product Builder Agent

This web application provides the same functionality as the command-line chat interface
but with a modern web UI using Gradio. Users can interact with the DPBuilderAgent through
a chat interface in their browser.
"""

import asyncio
import sys
import os
from pathlib import Path
import gradio as gr
import logging
from typing import List, Tuple, Optional

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dp_chat_agent.chat_agent import create_dp_composer_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('dp_builder_gradio.log')
    ],
    force=True
)
logger = logging.getLogger(__name__)

class GradioChatInterface:
    def __init__(self):
        self.agent = None
        self.session_id = None
        self.chat_history = []
        
    async def initialize_agent(self, initial_message: str = None):
        """Initialize the DPComposerAgent with a new session"""
        try:
            logger.info("Initializing Data Product Composer Agent...")
            
            # Create agent instance
            self.agent = create_dp_composer_agent(
                agent_name="Data Product Composer",
                user_message=initial_message or "Hello, I'm ready to help you build a data product!",
                model_name="gpt-4o-mini"
            )
            
            # Get the session ID that was created
            self.session_id = self.agent.session_id
            
            logger.info(f"Agent initialized with session ID: {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            return False
    
    async def process_message(self, user_input: str) -> str:
        """Process user message through the agent"""
        try:
            if not self.agent:
                return "Error: Agent not initialized. Please refresh the page."
            
            logger.info(f"Processing message: {user_input[:50]}...")
            
            # Run the agent with the user message
            result = await self.agent.run(current_message=user_input)
            
            # Extract the response from the result
            if isinstance(result, dict):
                if "error" in result:
                    return f"Error: {result['error']}"
                elif "reply" in result:
                    return result["reply"]
                else:
                    return str(result)
            else:
                return str(result)
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
    
    async def chat_function(self, message: str, history: List[List[str]]) -> Tuple[str, List[List[str]]]:
        """Handle chat messages and return response with updated history"""
        if not message.strip():
            return "", history
        
        # Add user message to history
        history.append([message, None])
        
        # Process the message
        response = await self.process_message(message)
        
        # Update history with response
        history[-1][1] = response
        
        return "", history
    
    async def clear_chat(self) -> List[List[str]]:
        """Clear chat history and reinitialize agent"""
        try:
            # Reinitialize agent with a fresh session
            await self.initialize_agent()
            self.chat_history = []
            return []
        except Exception as e:
            logger.error(f"Error clearing chat: {e}")
            return self.chat_history

# Global instance
chat_interface = GradioChatInterface()

async def initialize_app():
    """Initialize the chat interface"""
    await chat_interface.initialize_agent()

def create_gradio_interface():
    """Create and configure the Gradio interface"""
    
    # Custom CSS for better styling
    css = """
    .gradio-container {
        max-width: 1200px !important;
        margin: auto !important;
    }
    .chat-message {
        padding: 10px;
        margin: 5px 0;
        border-radius: 10px;
    }
    .user-message {
        background-color: #e3f2fd;
        margin-left: 20%;
    }
    .bot-message {
        background-color: #f5f5f5;
        margin-right: 20%;
    }
    """
    
    with gr.Blocks(css=css, title="Data Product Composer Chat") as interface:
        gr.Markdown("""
        # 🤖 Data Product Composer Chat
        
        Welcome! I'm here to help you build comprehensive data products.
                
        **Instructions:**
        • Type your message in the chat box below
        • Use the "Clear Chat" button to start a new session
        """)
        
        with gr.Row():
            with gr.Column(scale=3):
                # Chat interface
                chatbot = gr.Chatbot(
                    label="Chat with Data Product Composer",
                    height=500,
                    show_label=True,
                    container=True,
                    bubble_full_width=False
                )
                
                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="Type your message here...",
                        label="Your Message",
                        lines=2,
                        scale=4
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)
                
                with gr.Row():
                    clear_btn = gr.Button("Clear Chat", variant="secondary")
            
            with gr.Column(scale=1):
                # Instructions panel
                gr.Markdown("""
                ### 💡 Tips
                - Be specific about your data product requirements
                - Ask about data contracts, field definitions, or validation rules
                - The agent will guide you through the complete data product creation process
                """)
        
        # Event handlers
        def handle_send(message, history):
            """Handle send button click"""
            if not message.strip():
                return "", history
            
            # Run the async chat function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                new_message, updated_history = loop.run_until_complete(
                    chat_interface.chat_function(message, history)
                )
                return new_message, updated_history
            finally:
                loop.close()
        
        def handle_clear():
            """Handle clear button click"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                cleared_history = loop.run_until_complete(
                    chat_interface.clear_chat()
                )
                return cleared_history
            finally:
                loop.close()
        
        # Connect event handlers
        send_btn.click(
            handle_send,
            inputs=[msg_input, chatbot],
            outputs=[msg_input, chatbot]
        )
        
        msg_input.submit(
            handle_send,
            inputs=[msg_input, chatbot],
            outputs=[msg_input, chatbot]
        )
        
        clear_btn.click(
            handle_clear,
            inputs=[],
            outputs=[chatbot]
        )
    
    return interface

def main():
    """Main entry point for the Gradio app"""
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable is required")
        print("Please set your OpenAI API key and try again.")
        sys.exit(1)
    
    # Initialize the chat interface
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(initialize_app())
    finally:
        loop.close()
    
    # Create and launch the Gradio interface
    interface = create_gradio_interface()
    
    print("🚀 Starting Data Product Composer Chat Web Interface...")
    print("📱 The interface will be available in your browser")
    
    # Launch the interface
    interface.launch(
        server_name="0.0.0.0",  # Allow external access
        server_port=7860,       # Default Gradio port
        share=False,            # Set to True if you want a public link
        show_error=True,        # Show errors in the interface
        quiet=False,            # Show startup messages
        inbrowser=True          # Open browser automatically
    )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Chat interface terminated by user.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
