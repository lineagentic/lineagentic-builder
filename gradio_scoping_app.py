#!/usr/bin/env python3
"""
Gradio App for Data Product Scoping Agent
Provides a user-friendly interface for data product scoping
"""

import gradio as gr
import asyncio
import os
import json
from typing import Dict, Any
from contextlib import AsyncExitStack
from agents.mcp.server import MCPServerStdio

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Check for OpenAI API key
if not os.getenv("OPENAI_API_KEY"):
    print("Warning: OPENAI_API_KEY not found in .env file")
    print("Please create a .env file with your OpenAI API key")

class GradioScopingApp:
    """Gradio app wrapper for the data product scoping agent"""
    
    def __init__(self):
        self.mcp_server = None
        self.current_result = None
        
    async def connect_mcp_server(self) -> str:
        """Connect to the MCP server"""
        try:
            # Import the MCP server parameters
            from dp_server.mcp_params import agentic_mcp_server_params
            
            # Connect to the MCP server directly without context manager
            self.mcp_server = MCPServerStdio(agentic_mcp_server_params[0], client_session_timeout_seconds=120)
            
            # Initialize the connection
            await self.mcp_server.__aenter__()
            
            # Test the connection
            result = await self.mcp_server.call_tool("get_conversation_state", {})
            if result.isError:
                return f"❌ MCP server connection failed: {result.content}"
            
            return "✅ Successfully connected to MCP server"
                
        except Exception as e:
            return f"❌ Error connecting to MCP server: {str(e)}"
    
    async def run_scoping(self, user_requirements: str) -> str:
        """Run the scoping agent with user requirements"""
        if not self.mcp_server:
            return "❌ Please connect to MCP server first using the 'Connect to MCP Server' button"
        
        if not user_requirements.strip():
            return "❌ Please provide user requirements for scoping"
        
        try:
            # Check if server is still connected
            if not hasattr(self.mcp_server, 'call_tool'):
                return "❌ MCP server connection lost. Please reconnect."
            
            print(f"Debug: Calling scoping_agent tool with message: {user_requirements[:100]}...")
            
            # Call the scoping agent tool directly
            result = await self.mcp_server.call_tool("scoping_agent", {"message": user_requirements})
            
            print(f"Debug: Tool call result: {result}")
            
            if result.isError:
                return f"❌ Error calling scoping agent: {result.content}"
            
            # Parse the result
            try:
                # Extract the structured content
                if hasattr(result, 'structuredContent') and result.structuredContent:
                    scoping_result = result.structuredContent.get('result', {})
                else:
                    # Fallback to text content
                    scoping_result = json.loads(result.content[0].text)
                
                # Store the result
                self.current_result = scoping_result
                
                # Format the output
                return self._format_result(scoping_result)
                
            except Exception as parse_error:
                return f"❌ Error parsing result: {str(parse_error)}\n\nRaw result: {result.content}"
                
        except Exception as e:
            print(f"Debug: Exception in run_scoping: {e}")
            import traceback
            traceback.print_exc()
            return f"❌ Error running scoping agent: {str(e)}"
    
    def _format_result(self, result: Dict[str, Any]) -> str:
        """Format the agent result for display"""
        try:
            # Try to extract the main response
            if isinstance(result, dict):
                if "response" in result:
                    main_response = result["response"]
                elif "reply" in result:
                    main_response = result["reply"]
                elif "final_output" in result:
                    main_response = result["final_output"]
                else:
                    main_response = str(result)
            else:
                main_response = str(result)
            
            # Format the output
            formatted_output = f"""
## 🎯 Scoping Results

### Main Response:
{main_response}

### Full Result:
```json
{json.dumps(result, indent=2)}
```
"""
            return formatted_output
            
        except Exception as e:
            return f"Result received but error formatting: {str(e)}\n\nRaw result: {result}"
    
    async def get_conversation_state(self) -> str:
        """Get the current conversation state"""
        if not self.mcp_server:
            return "❌ No MCP server connection. Please connect first."
        
        try:
            result = await self.mcp_server.call_tool("get_conversation_state", {})
            if result.isError:
                return f"❌ Error getting conversation state: {result.content}"
            
            # Parse the result
            if hasattr(result, 'structuredContent') and result.structuredContent:
                state = result.structuredContent.get('result', {})
            else:
                state = json.loads(result.content[0].text)
            
            return f"✅ Current state: {json.dumps(state, indent=2)}"
            
        except Exception as e:
            return f"❌ Error getting conversation state: {str(e)}"
    
    async def reset_conversation(self) -> str:
        """Reset the conversation state"""
        if not self.mcp_server:
            return "❌ No MCP server connection. Please connect first."
        
        try:
            result = await self.mcp_server.call_tool("reset_conversation", {})
            if result.isError:
                return f"❌ Error resetting conversation: {result.content}"
            
            self.current_result = None
            return "✅ Conversation reset successfully"
            
        except Exception as e:
            return f"❌ Error resetting conversation: {str(e)}"
    
    async def disconnect_mcp_server(self) -> str:
        """Disconnect from the MCP server"""
        try:
            if self.mcp_server:
                await self.mcp_server.__aexit__(None, None, None)
                self.mcp_server = None
                self.current_result = None
                return "✅ Disconnected from MCP server"
            else:
                return "✅ No active connection to disconnect"
        except Exception as e:
            return f"❌ Error disconnecting: {str(e)}"

    async def check_connection_status(self) -> str:
        """Check the current connection status"""
        try:
            if not self.mcp_server:
                return "❌ No MCP server connection"
            
            if not hasattr(self.mcp_server, 'call_tool'):
                return "❌ MCP server object is invalid"
            
            # Try a simple tool call to test connection
            result = await self.mcp_server.call_tool("get_conversation_state", {})
            if result.isError:
                return f"❌ Connection test failed: {result.content}"
            
            return "✅ MCP server connection is active and working"
            
        except Exception as e:
            return f"❌ Connection check failed: {str(e)}"

    async def process_chat_message(self, history):
        """Process a chat message and generate response"""
        if not history or not history[-1][0]:
            return history, "No message to process"
        
        if not self.mcp_server:
            # Add error message to chat
            history[-1][1] = "❌ Please connect to MCP server first using the 'Connect to MCP Server' button"
            return history, "Connection required"
        
        user_message = history[-1][0]
        
        try:
            # Check if server is still connected
            if not hasattr(self.mcp_server, 'call_tool'):
                history[-1][1] = "❌ MCP server connection lost. Please reconnect."
                return history, "Connection lost"
            
            print(f"Debug: Processing chat message: {user_message[:100]}...")
            
            # Call the scoping agent tool directly
            result = await self.mcp_server.call_tool("scoping_agent", {"message": user_message})
            
            print(f"Debug: Tool call result: {result}")
            
            if result.isError:
                history[-1][1] = f"❌ Error calling scoping agent: {result.content}"
                return history, f"Error: {result.content}"
            
            # Parse the result
            try:
                # Extract the structured content
                if hasattr(result, 'structuredContent') and result.structuredContent:
                    scoping_result = result.structuredContent.get('result', {})
                else:
                    # Fallback to text content
                    scoping_result = json.loads(result.content[0].text)
                
                # Store the result
                self.current_result = scoping_result
                
                # Extract the response for chat
                if isinstance(scoping_result, dict):
                    if "response" in scoping_result:
                        bot_response = scoping_result["response"]
                    elif "reply" in scoping_result:
                        bot_response = scoping_result["reply"]
                    else:
                        bot_response = str(scoping_result)
                else:
                    bot_response = str(scoping_result)
                
                # Add bot response to chat
                history[-1][1] = bot_response
                
                # Format the full result for display
                formatted_result = self._format_result(scoping_result)
                
                return history, formatted_result
                
            except Exception as parse_error:
                error_msg = f"❌ Error parsing result: {str(parse_error)}"
                history[-1][1] = error_msg
                return history, f"Parse error: {str(parse_error)}"
                
        except Exception as e:
            print(f"Debug: Exception in process_chat_message: {e}")
            import traceback
            traceback.print_exc()
            error_msg = f"❌ Error processing message: {str(e)}"
            history[-1][1] = error_msg
            return history, f"Processing error: {str(e)}"

def create_gradio_interface():
    """Create the Gradio interface"""
    app = GradioScopingApp()
    
    # Get configuration from environment variables
    server_port = int(os.getenv("GRADIO_SERVER_PORT", 7860))
    server_name = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
    
    with gr.Blocks(
        title="Data Product Scoping Agent",
        theme=gr.themes.Soft(),
        css="""
        .main-header {
            text-align: center;
            margin-bottom: 20px;
            color: #2c3e50;
        }
        .result-box {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        }
        """
    ) as interface:
        
        # Header
        gr.Markdown(
            """
            # 🎯 Data Product Scoping Agent
            
            This tool helps you define and scope data products by analyzing your requirements 
            and extracting key information using AI-powered analysis.
            
            **Required Fields:** name, domain, owner, purpose, upstreams
            """,
            elem_classes=["main-header"]
        )
        
        with gr.Row():
            with gr.Column(scale=1):
                # MCP Server Connection Section
                gr.Markdown("### 🔌 MCP Server Connection")
                
                connect_btn = gr.Button("🔌 Connect to MCP Server", variant="primary")
                connect_output = gr.Textbox(label="Connection Status", interactive=False)
                
                gr.Markdown("---")
                
                # Control Section
                gr.Markdown("### ⚙️ Controls")
                
                status_btn = gr.Button("🔍 Check Connection Status")
                status_output = gr.Textbox(label="Connection Status", interactive=False)
                
                state_btn = gr.Button("📊 Get State")
                state_output = gr.Textbox(label="Conversation State", interactive=False)
                
                reset_btn = gr.Button("🔄 Reset Conversation", variant="secondary")
                reset_output = gr.Textbox(label="Reset Status", interactive=False)
                
                disconnect_btn = gr.Button("❌ Disconnect", variant="stop")
                disconnect_output = gr.Textbox(label="Disconnect Status", interactive=False)
            
            with gr.Column(scale=2):
                # Main Scoping Section
                gr.Markdown("### 💬 Chat with Scoping Agent")
                
                # Chat interface
                chatbot = gr.Chatbot(
                    label="Scoping Agent Chat",
                    height=400,
                    show_label=True
                )
                
                with gr.Row():
                    msg = gr.Textbox(
                        label="Type your message",
                        placeholder="Describe your data product requirements or ask questions...",
                        lines=2,
                        scale=4
                    )
                    send_btn = gr.Button("💬 Send", variant="primary", scale=1)
                
                # Clear chat button
                clear_btn = gr.Button("🗑️ Clear Chat", variant="secondary")
                
                gr.Markdown("---")
                
                # Results Section
                gr.Markdown("### 📊 Scoping Results")
                results_output = gr.Markdown(
                    value="Start chatting with the scoping agent to see results here...",
                    elem_classes=["result-box"]
                )
        
        # Event handlers
        connect_btn.click(
            fn=app.connect_mcp_server,
            inputs=[],
            outputs=connect_output
        )
        
        # Chat functionality
        def user_message(message, history):
            """Handle user message in chat"""
            if not message.strip():
                return history, ""
            
            # Add user message to chat
            history.append([message, None])
            return history, ""
        
        def bot_response(history):
            """Generate bot response using MCP server"""
            if not history or not history[-1][0]:
                return history
            
            user_message = history[-1][0]
            
            # This will be handled by the async function
            return history
        
        # Chat event handlers
        msg.submit(
            fn=user_message,
            inputs=[msg, chatbot],
            outputs=[chatbot, msg]
        )
        
        send_btn.click(
            fn=user_message,
            inputs=[msg, chatbot],
            outputs=[chatbot, msg]
        ).then(
            fn=app.process_chat_message,
            inputs=[chatbot],
            outputs=[chatbot, results_output]
        )
        
        clear_btn.click(
            fn=lambda: ([], "Chat cleared!"),
            inputs=[],
            outputs=[chatbot, results_output]
        )
        
        status_btn.click(
            fn=app.check_connection_status,
            inputs=[],
            outputs=status_output
        )
        
        state_btn.click(
            fn=app.get_conversation_state,
            inputs=[],
            outputs=state_output
        )
        
        reset_btn.click(
            fn=app.reset_conversation,
            inputs=[],
            outputs=reset_output
        )
        
        disconnect_btn.click(
            fn=app.disconnect_mcp_server,
            inputs=[],
            outputs=disconnect_output
        )
        
        # Instructions
        gr.Markdown("""
        ---
        ### 📖 How to Use
        
        1. **Connect**: Click "Connect to MCP Server" to establish connection
        2. **Chat**: Type your data product requirements in the chat and press Enter or click Send
        3. **Iterate**: Continue the conversation to refine your data product scope
        4. **Review**: Check the results section for detailed scoping information
        5. **Manage**: Use "Get State" to see current progress, "Reset" to start fresh
        6. **Disconnect**: Use "Disconnect" when done
        
        ### 💡 Tips for Better Results
        
        - Start with a general description of your data product idea
        - Be specific about your business domain and purpose
        - Include all relevant data sources and dependencies
        - Specify who will own and maintain the data product
        - Describe the business value and use cases clearly
        - Ask follow-up questions to clarify any unclear aspects
        """)
    
    return interface

def main():
    """Main function to run the Gradio app"""
    print("🚀 Starting Data Product Scoping Agent Gradio App...")
    
    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not found in .env file")
        print("   Please create a .env file with your OpenAI API key")
        print("   The launcher script will create a template for you")
    
    # Create and launch the interface
    interface = create_gradio_interface()
    
    # Get configuration from environment variables
    server_port = int(os.getenv("GRADIO_SERVER_PORT", 7860))
    server_name = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
    
    # Launch with configuration
    interface.launch(
        server_name=server_name,
        server_port=server_port,
        share=False,              # Set to True if you want a public URL
        show_error=True,         # Show detailed errors
        quiet=False              # Show launch info
    )

if __name__ == "__main__":
    main()
