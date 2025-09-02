#!/usr/bin/env python3
"""
Chat application for interacting with the DP Builder Agent.
Provides both command-line and interactive chat interfaces.
"""

import asyncio
import argparse
import sys
import os
from typing import Optional, Dict, Any
import json
from pathlib import Path

# Add the dp_server directory to the Python path
sys.path.append(str(Path(__file__).parent / "dp_server"))

from dp_builder_agent import create_dp_builder_agent, DPBuilderAgent


class ChatInterface:
    """Interactive chat interface for the DP Builder Agent."""
    
    def __init__(self, agent_name: str = "DataProductBuilder", model_name: str = "gpt-4o-mini"):
        self.agent_name = agent_name
        self.model_name = model_name
        self.agent: Optional[DPBuilderAgent] = None
        self.conversation_history = []
        
    async def initialize_agent(self, initial_message: str = ""):
        """Initialize the DP Builder Agent."""
        try:
            print(f"🤖 Initializing {self.agent_name}...")
            self.agent = create_dp_builder_agent(
                agent_name=self.agent_name,
                user_message=initial_message or "Ready to help with data product analysis",
                model_name=self.model_name
            )
            
            print(f"✅ {self.agent_name} initialized successfully!")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize agent: {e}")
            return False
    
    async def send_message(self, message: str) -> Dict[str, Any]:
        """Send a message to the agent and get response."""
        if not self.agent:
            return {"error": "Agent not initialized"}
        
        try:
            print(f"\n💬 Sending message: {message}")
            print("⏳ Processing...")
            
            # Add message to conversation history
            self.conversation_history.append({"role": "user", "content": message})
            
            # Use the session-based method to maintain state across messages
            result = await self.agent.run_with_session(message)
            
            # Add response to conversation history
            if "error" not in result:
                self.conversation_history.append({"role": "assistant", "content": str(result)})
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing message: {e}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}
    
    def display_response(self, response: Dict[str, Any]):
        """Display the agent's response in a formatted way."""
        print("\n" + "="*60)
        print("🤖 AGENT RESPONSE:")
        print("="*60)
        
        if "error" in response:
            print(f"❌ Error: {response['error']}")
        else:
            # Try to pretty print JSON if it's JSON-like
            try:
                if isinstance(response, dict):
                    print(json.dumps(response, indent=2))
                else:
                    print(str(response))
            except:
                print(str(response))
        
        print("="*60)
    
    async def interactive_chat(self):
        """Run an interactive chat session."""
        print(f"\n🚀 Starting interactive chat with {self.agent_name}")
        print("Type 'quit', 'exit', or 'bye' to end the session")
        print("Type 'help' for available commands")
        print("Type 'history' to see conversation history")
        print("-" * 60)
        
        while True:
            try:
                # Get user input
                user_input = input("\n💬 You: ").strip()
                
                if not user_input:
                    continue
                
                # Check for commands
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("👋 Goodbye! Thanks for using the DP Builder Agent.")
                    break
                elif user_input.lower() == 'help':
                    self.show_help()
                    continue
                elif user_input.lower() == 'history':
                    self.show_conversation_history()
                    continue
                elif user_input.lower() == 'clear':
                    self.conversation_history.clear()
                    print("🗑️ Conversation history cleared.")
                    continue
                
                # Send message to agent
                response = await self.send_message(user_input)
                self.display_response(response)
                
            except KeyboardInterrupt:
                print("\n\n👋 Chat interrupted. Goodbye!")
                break
            except EOFError:
                print("\n\n👋 End of input. Goodbye!")
                break
    
    def show_help(self):
        """Show available commands."""
        print("\n📚 Available Commands:")
        print("  help     - Show this help message")
        print("  history  - Show conversation history")
        print("  clear    - Clear conversation history")
        print("  quit     - Exit the chat session")
        print("  exit     - Exit the chat session")
        print("  bye      - Exit the chat session")
        print("\n💡 Just type your message normally to chat with the agent!")
    
    def show_conversation_history(self):
        """Show the conversation history."""
        if not self.conversation_history:
            print("📝 No conversation history yet.")
            return
        
        print("\n📝 Conversation History:")
        print("-" * 60)
        for i, msg in enumerate(self.conversation_history, 1):
            role = msg["role"].upper()
            content = msg["content"][:100] + "..." if len(str(msg["content"])) > 100 else str(msg["content"])
            print(f"{i}. {role}: {content}")
        print("-" * 60)


async def single_message_mode(agent_name: str, message: str, model_name: str):
    """Run the agent with a single message."""
    try:
        print(f"🤖 Initializing {agent_name}...")
        agent = create_dp_builder_agent(
            agent_name=agent_name,
            user_message=message,
            model_name=model_name
        )
        
        print(f"💬 Processing message: {message}")
        result = await agent.run(current_message=message)
        
        print("\n" + "="*60)
        print("🤖 AGENT RESPONSE:")
        print("="*60)
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            try:
                if isinstance(result, dict):
                    print(json.dumps(result, indent=2))
                else:
                    print(str(result))
            except:
                print(str(result))
        
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True


def main():
    """Main entry point for the chat application."""
    parser = argparse.ArgumentParser(
        description="Chat with the DP Builder Agent for data product analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive chat mode
  python chat.py
  
  # Single message mode
  python chat.py -m "I want to create a data product for customer analytics"
  
  # Custom agent name and model
  python chat.py -a "MyAgent" -m "gpt-4" -i "Create a data product for sales analysis"
        """
    )
    
    parser.add_argument(
        "-m", "--message",
        help="Single message to send to the agent (non-interactive mode)"
    )
    
    parser.add_argument(
        "-a", "--agent-name",
        default="DataProductBuilder",
        help="Name for the agent (default: DataProductBuilder)"
    )
    
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="Model to use (default: gpt-4o-mini)"
    )
    
    parser.add_argument(
        "-i", "--initial-message",
        default="",
        help="Initial message to initialize the agent with"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="DP Builder Agent Chat v1.0.0"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.message and args.initial_message:
        print("❌ Error: Cannot use both --message and --initial-message")
        sys.exit(1)
    
    try:
        if args.message:
            # Single message mode
            print("🚀 Single Message Mode")
            success = asyncio.run(single_message_mode(
                agent_name=args.agent_name,
                message=args.message,
                model_name=args.model
            ))
            sys.exit(0 if success else 1)
        else:
            # Interactive mode
            print("🚀 Interactive Chat Mode")
            chat_interface = ChatInterface(
                agent_name=args.agent_name,
                model_name=args.model
            )
            
            # Initialize agent if initial message provided
            if args.initial_message:
                asyncio.run(chat_interface.initialize_agent(args.initial_message))
            else:
                # Initialize agent with default message if no initial message provided
                asyncio.run(chat_interface.initialize_agent())
            
            # Start interactive chat
            asyncio.run(chat_interface.interactive_chat())
            
    except KeyboardInterrupt:
        print("\n\n👋 Chat interrupted. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()