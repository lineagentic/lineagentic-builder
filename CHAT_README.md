# Data Product Builder Chat Interface

## Overview

The `chat.py` file provides an interactive command-line interface for the Data Product Builder Agent. This chat application creates a single instance of the DPBuilderAgent and maintains conversation state throughout the session.

## Features

- **Single Agent Instance**: One agent per chat session with persistent state
- **Session Management**: Automatic session creation and persistence via JSON files
- **Interactive CLI**: User-friendly command-line interface
- **State Persistence**: Conversation history and data product state saved automatically
- **Error Handling**: Robust error handling and recovery
- **Special Commands**: Built-in commands for help, status, and session management

## Usage

### Prerequisites

1. Set your OpenAI API key:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

2. Install dependencies:
   ```bash
   pip install -e .
   ```

### Running the Chat

```bash
python chat.py
```

### Chat Commands

- **Normal conversation**: Just type your message and press Enter
- **`help`**: Show help message and available commands
- **`status`**: Display current session information
- **`quit`/`exit`/`bye`**: End the chat session
- **`Ctrl+C`**: Interrupt and exit the chat

## Architecture

```
chat.py (CLI Interface)
    ↓
DPBuilderAgent (Single Instance)
    ↓
MCP Servers (scoping_agent, data_contract_agent)
    ↓
Session Files (JSON persistence in dp_server/sessions/)
```

## Session Management

- **Automatic Session Creation**: Each chat session gets a unique UUID
- **State Persistence**: Conversation state saved to `dp_server/sessions/conversation_state_{session_id}.json`
- **Conversation History**: All messages stored in the session file
- **Data Product State**: Extracted data product information persisted across interactions

## Example Session

```
🤖 Data Product Builder Chat
============================================================
Welcome! I'm here to help you build comprehensive data products.

💬 You: I want to create a data product for customer analytics

🤖 Agent: I'll help you build a comprehensive data product for customer analytics. Let me start by understanding your requirements...

💬 You: We need to track customer behavior, purchase history, and demographics

🤖 Agent: Great! Let me gather more details about your customer analytics data product...

💬 You: status

📊 Session Status:
   Session ID: be51f03a-2f48-4c89-9901-d7b89a53477e
   Agent: Data Product Builder
   Model: gpt-4o-mini

💬 You: quit

👋 Goodbye! Your session has been saved.
```

## Technical Details

### Why This Approach?

1. **Session Management**: The agent already has robust session management built-in
2. **Single Instance**: Designed to maintain conversation state across multiple interactions
3. **Simplicity**: Direct Python method calls are more efficient than WebSockets for CLI
4. **State Persistence**: Automatic JSON file persistence allows conversation continuity

### Session Flow

1. **Initialization**: Agent creates new session with unique UUID
2. **Message Processing**: Each message processed through the agent's MCP servers
3. **State Updates**: Conversation state updated and saved after each interaction
4. **Persistence**: Session data saved to JSON file for future retrieval

### Error Handling

- **Agent Initialization**: Graceful handling of initialization failures
- **Message Processing**: Error recovery for individual message failures
- **Session Management**: Automatic fallback to default state if session files corrupted
- **User Interruption**: Clean handling of Ctrl+C and EOF

## Development

The chat interface is designed to be:
- **Extensible**: Easy to add new commands or features
- **Maintainable**: Clean separation of concerns
- **Robust**: Comprehensive error handling
- **User-Friendly**: Clear feedback and instructions
