#!/usr/bin/env python3
"""
Simple Gradio chat app for the Scoping Agent.
"""
import gradio as gr
import asyncio
import json
import os
from typing import List, Tuple
from pathlib import Path
import sys
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from scoping_agent import ScopingAgentStructured, Message

class ScopingAgentChat:
    def __init__(self):
        """Initialize the chat interface with the scoping agent."""
        # Load environment variables from .env file
        load_dotenv()
        
        # Mock OpenAI client for demo (you'll need to set OPENAI_API_KEY in .env)
        class MockOpenAI:
            def __init__(self):
                self.chat = self.Chat()
            
            class Chat:
                def __init__(self):
                    self.completions = self.Completions()
                
                class Completions:
                    def create(self, **kwargs):
                        # Mock response for demo
                        return type('Response', (), {
                            'choices': [type('Choice', (), {
                                'message': type('Message', (), {
                                    'content': json.dumps({
                                        "reply": "This is a mock response. Please set OPENAI_API_KEY environment variable for real responses.",
                                        "confidence": 0.8,
                                        "next_action": "provide_name",
                                        "metadata": {},
                                        "extracted_data": {},
                                        "missing_fields": ["name", "domain", "owner", "purpose", "upstreams"]
                                    })
                                })()
                            })()]
                        })()
        
        try:
            # Try to use real OpenAI client
            from openai import OpenAI
            self.agent = ScopingAgentStructured()
            print("✅ Using real OpenAI client")
        except Exception as e:
            print(f"⚠️ Using mock OpenAI client: {e}")
            print("   Make sure to create a .env file with your OPENAI_API_KEY")
            self.agent = ScopingAgentStructured(openai_client=MockOpenAI())
        
        self.conversation_state = {
            "data_product": {},
            "history": []
        }
    
    def chat_with_agent(self, message: str, history: List[List[str]]) -> Tuple[str, List[List[str]]]:
        """Chat with the scoping agent."""
        if not message.strip():
            return "", history
        
        try:
            # Create message object
            user_message = Message(role="user", content=message)
            
            # Add to conversation history
            self.conversation_state["history"].append({
                "role": "user",
                "content": message
            })
            
            # Get agent response
            response = asyncio.run(self.agent.handle_async(self.conversation_state, user_message))
            
            # Extract reply
            agent_reply = response.get("reply", "No response received")
            
            # Add agent response to history
            self.conversation_state["history"].append({
                "role": "assistant", 
                "content": agent_reply
            })
            
            # Update history for Gradio
            history.append([message, agent_reply])
            
            # Show current state info
            data_product = self.conversation_state.get("data_product", {})
            if data_product:
                state_info = "\n\n**Current Data Product State:**\n"
                for key, value in data_product.items():
                    if value:
                        state_info += f"- {key}: {value}\n"
                agent_reply += state_info
            
            return "", history
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            history.append([message, error_msg])
            return "", history
    
    def reset_conversation(self) -> Tuple[str, List[List[str]]]:
        """Reset the conversation state."""
        self.conversation_state = {
            "data_product": {},
            "history": []
        }
        return "", []
    
    def show_current_state(self) -> str:
        """Show the current conversation state."""
        data_product = self.conversation_state.get("data_product", {})
        if not data_product:
            return "No data product information captured yet."
        
        state_info = "**Current Data Product State:**\n"
        for key, value in data_product.items():
            if value:
                state_info += f"- {key}: {value}\n"
        
        return state_info

def create_chat_interface():
    """Create the Gradio chat interface."""
    chat_agent = ScopingAgentChat()
    
    with gr.Blocks(title="Scoping Agent Chat", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🤖 Scoping Agent Chat")
        gr.Markdown("Chat with the AI agent to scope your data product. The agent will help you define:")
        gr.Markdown("- **name**: Data product name")
        gr.Markdown("- **domain**: Business domain (sales, finance, marketing, operations)")
        gr.Markdown("- **owner**: Owner (email, team ID, or person)")
        gr.Markdown("- **purpose**: Purpose and use case")
        gr.Markdown("- **upstreams**: List of upstream data sources (optional)")
        
        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="Chat with Scoping Agent",
                    height=500,
                    show_label=True
                )
                
                with gr.Row():
                    msg = gr.Textbox(
                        label="Your message",
                        placeholder="Tell me about your data product...",
                        scale=4
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)
                
                with gr.Row():
                    clear_btn = gr.Button("Clear Chat", variant="secondary")
                    reset_btn = gr.Button("Reset State", variant="secondary")
            
            with gr.Column(scale=1):
                gr.Markdown("### Current State")
                state_display = gr.Textbox(
                    label="Data Product State",
                    value="No data product information captured yet.",
                    lines=10,
                    interactive=False
                )
                refresh_state_btn = gr.Button("Refresh State", variant="secondary")
        
        # Event handlers
        def send_message(message, history):
            return chat_agent.chat_with_agent(message, history)
        
        def clear_chat():
            return "", []
        
        def reset_state():
            return chat_agent.reset_conversation()
        
        def refresh_state():
            return chat_agent.show_current_state()
        
        # Connect events
        send_btn.click(
            send_message,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot]
        )
        
        msg.submit(
            send_message,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot]
        )
        
        clear_btn.click(
            clear_chat,
            outputs=[msg, chatbot]
        )
        
        reset_btn.click(
            reset_state,
            outputs=[msg, chatbot]
        )
        
        refresh_state_btn.click(
            refresh_state,
            outputs=[state_display]
        )
        
        # Auto-refresh state after each message
        def auto_refresh_state(message, history):
            _, new_history = send_message(message, history)
            return chat_agent.show_current_state()
        
        send_btn.click(
            auto_refresh_state,
            inputs=[msg, chatbot],
            outputs=[state_display]
        )
        
        msg.submit(
            auto_refresh_state,
            inputs=[msg, chatbot],
            outputs=[state_display]
        )
    
    return demo

if __name__ == "__main__":
    # Create and launch the app
    app = create_chat_interface()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        debug=True
    )
