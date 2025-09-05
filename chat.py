#!/usr/bin/env python3
"""
Interactive Chat Interface for Data Product Builder Agent

This chat application creates a single instance of the DPBuilderAgent and maintains
conversation state throughout the session. The agent handles session management
internally, persisting conversation state to JSON files.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dp_chat_agent.chat_agent import create_dp_composer_agent
import logging

# Configure logging with both console and file output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('dp_builder.log')  # File output
    ],
    force=True  # Override any existing configuration
)
logger = logging.getLogger(__name__)

class ChatInterface:
    def __init__(self):
        self.agent = None
        self.session_id = None
        self.running = True
        
    async def initialize_agent(self, initial_message: str = None):
        """Initialize the DPComposerAgent with a new session"""
        try:
            logger.info("Initializing Data Product Composer Agent...")
            
            # Create agent instance - it will handle session creation internally
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
                return "Error: Agent not initialized. Please restart the chat."
            
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
                    # Handle other result formats
                    return str(result)
            else:
                return str(result)
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
    
    def print_welcome(self):
        """Print welcome message and instructions"""
        print("\n" + "="*60)
        print("Lineagentic-DPC: Data Product Composer")
        print("="*60)
        print("Welcome! I'm here to help you build comprehensive data products.")
        print("\nI can help you with:")
        print("• Data product scoping and requirements")
        print("• Data contract definition")
        print("• Field extraction and validation")
        print("• Metadata extraction")
        print("\nCommands:")
        print("• Type your message and press Enter to chat")
        print("• Type 'quit', 'exit', or 'bye' to end the session")
        print("• Type 'help' for this message")
        print("• Type 'status' to see session information")
        print("="*60 + "\n")
    
    def print_status(self):
        """Print current session status"""
        print(f"\n📊 Session Status:")
        print(f"   Session ID: {self.session_id}")
        print(f"   Agent: {self.agent.agent_name if self.agent else 'Not initialized'}")
        print(f"   Model: {self.agent.model_name if self.agent else 'N/A'}")
        print()
    
    async def run(self):
        """Main chat loop"""
        self.print_welcome()
        
        # Initialize agent
        if not await self.initialize_agent():
            print("❌ Failed to initialize agent. Please check your configuration.")
            return
        
        print("✅ Agent initialized successfully!")
        self.print_status()
        
        # Main chat loop
        while self.running:
            try:
                # Get user input
                user_input = input("\n💬 You: ").strip()
                
                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("\n👋 Goodbye! Your session has been saved.")
                    break
                elif user_input.lower() == 'help':
                    self.print_welcome()
                    continue
                elif user_input.lower() == 'status':
                    self.print_status()
                    continue
                elif not user_input:
                    print("Please enter a message or command.")
                    continue
                
                # Process the message
                print("\n🤖 Agent: ", end="", flush=True)
                response = await self.process_message(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\n\n👋 Chat interrupted. Goodbye!")
                break
            except EOFError:
                print("\n\n👋 Chat ended. Goodbye!")
                break
            except Exception as e:
                logger.error(f"Unexpected error in chat loop: {e}")
                print(f"\n❌ Unexpected error: {e}")
                print("Please try again or restart the chat.")

async def main():
    """Main entry point"""
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable is required")
        print("Please set your OpenAI API key and try again.")
        sys.exit(1)
    
    # Create and run chat interface
    chat = ChatInterface()
    await chat.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Chat terminated by user.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"❌ Fatal error: {e}")
        sys.exit(1)