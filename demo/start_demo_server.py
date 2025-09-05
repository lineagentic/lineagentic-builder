#!/usr/bin/env python3
"""
Start script for Lineagentic-DPC: Data Product Composer Demo
This is the entry point for Gradio deployment.
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import and run the demo server
from demo_server import create_gradio_interface, initialize_app
import asyncio

def main():
    """Main entry point for the demo server"""
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable is required")
        print("Please set your OpenAI API key and try again.")
        sys.exit(1)
    
    # Initialize the app
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(initialize_app())
    finally:
        loop.close()
    
    # Create and launch the interface
    interface = create_gradio_interface()
    
    print("🚀 Starting Lineagentic-DPC: Data Product Composer Demo...")
    print("📱 The interface will be available in your browser")
    
    # Launch the interface
    interface.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        quiet=False,
        inbrowser=False  # Don't open browser in deployment
    )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Demo server terminated by user.")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
