#!/usr/bin/env python3
"""
Test script for the Gradio chat interface
This script tests the basic functionality without launching the full web interface
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from gradio_chat import GradioChatInterface

async def test_chat_interface():
    """Test the basic functionality of the Gradio chat interface"""
    print("🧪 Testing Gradio Chat Interface...")
    
    # Create interface instance
    chat_interface = GradioChatInterface()
    
    # Test agent initialization
    print("1. Testing agent initialization...")
    success = await chat_interface.initialize_agent("Hello, this is a test message")
    if success:
        print("   ✅ Agent initialized successfully")
        print(f"   📋 Session ID: {chat_interface.session_id}")
    else:
        print("   ❌ Agent initialization failed")
        return False
    
    # Test message processing
    print("2. Testing message processing...")
    try:
        response = await chat_interface.process_message("I want to create a data product for customer analytics")
        if response and not response.startswith("Error:"):
            print("   ✅ Message processing successful")
            print(f"   💬 Response: {response[:100]}...")
        else:
            print(f"   ❌ Message processing failed: {response}")
            return False
    except Exception as e:
        print(f"   ❌ Message processing error: {e}")
        return False
    
    # Test session status
    print("3. Testing session status...")
    try:
        status = await chat_interface.get_session_status()
        if status and "Session ID" in status:
            print("   ✅ Session status retrieved successfully")
            print(f"   📊 Status: {status[:100]}...")
        else:
            print("   ❌ Session status failed")
            return False
    except Exception as e:
        print(f"   ❌ Session status error: {e}")
        return False
    
    # Test chat function
    print("4. Testing chat function...")
    try:
        history = []
        new_message, updated_history = await chat_interface.chat_function("What is a data product?", history)
        if updated_history and len(updated_history) > 0:
            print("   ✅ Chat function successful")
            print(f"   💬 History length: {len(updated_history)}")
        else:
            print("   ❌ Chat function failed")
            return False
    except Exception as e:
        print(f"   ❌ Chat function error: {e}")
        return False
    
    print("\n🎉 All tests passed! The Gradio interface is ready to use.")
    return True

def main():
    """Main test function"""
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable is required")
        print("Please set your OpenAI API key and try again.")
        sys.exit(1)
    
    # Run the tests
    try:
        success = asyncio.run(test_chat_interface())
        if success:
            print("\n✅ Test completed successfully!")
            print("You can now run 'python gradio_chat.py' to start the web interface.")
        else:
            print("\n❌ Tests failed. Please check the errors above.")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
