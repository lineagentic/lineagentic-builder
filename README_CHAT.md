# DP Builder Agent Chat Application

A comprehensive chat interface for interacting with the Data Product Builder Agent. This application provides both interactive and single-message modes for data product analysis.

## Features

- 🤖 **Interactive Chat Mode**: Real-time conversation with the DP Builder Agent
- 📝 **Single Message Mode**: Send one-off messages for quick analysis
- 💾 **Conversation History**: Track and review your conversation
- 🔧 **Customizable**: Set custom agent names and models
- 📊 **Data Product Analysis**: Comprehensive scoping and contract definition

## Installation

Make sure you have the required dependencies installed:

```bash
# Install the project dependencies
pip install -e .

# Or if using uv
uv sync
```

## Usage

### Interactive Chat Mode (Default)

Start an interactive chat session:

```bash
python chat.py
```

This will start a real-time chat where you can:
- Type messages and get responses from the agent
- Use commands like `help`, `history`, `clear`
- Exit with `quit`, `exit`, or `bye`

### Single Message Mode

Send a single message for analysis:

```bash
python chat.py -m "I want to create a data product for customer analytics"
```

### Advanced Options

```bash
# Custom agent name and model
python chat.py -a "MyCustomAgent" --model "gpt-4" -i "Initial setup message"

# Available options:
# -a, --agent-name: Custom name for the agent
# --model: AI model to use (default: gpt-4o-mini)
# -i, --initial-message: Initial message to set up the agent
# -m, --message: Single message mode (non-interactive)
```

## Commands

When in interactive mode, you can use these commands:

- `help` - Show available commands and help information
- `history` - Display conversation history
- `clear` - Clear conversation history
- `quit` / `exit` / `bye` - Exit the chat session

## Examples

### Starting a Data Product Analysis

```bash
# Interactive mode
python chat.py

# Then type:
# "I want to create a data product for customer analytics"
# "What are the key metrics I should track?"
# "Define the data schema for user behavior"
```

### Quick Analysis

```bash
# Single message for quick analysis
python chat.py -m "Analyze the scope for a sales performance data product"
```

## How It Works

The chat application:

1. **Connects** to the DP Builder Agent from `dp_server/dp_builder_agent.py`
2. **Initializes** the agent with your specified parameters
3. **Processes** messages through the agent's comprehensive analysis pipeline
4. **Maintains** conversation context and history
5. **Returns** structured analysis results for data product scoping and contract definition

## Architecture

```
chat.py → DPBuilderAgent → MCP Servers → Data Product Analysis
```

The application leverages:
- **DP Builder Agent**: Core analysis engine
- **MCP Servers**: Model Context Protocol servers for tool integration
- **Scoping Agent**: Analyzes data product requirements and boundaries
- **Data Contract Agent**: Defines schemas and validation rules

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're running from the project root directory
2. **Agent Initialization Failed**: Check that all dependencies are installed
3. **MCP Server Errors**: Verify the dp_server configuration

### Getting Help

```bash
# Show help
python chat.py --help

# Check version
python chat.py --version
```

## Development

The chat application is built with:
- **asyncio**: For asynchronous operations
- **argparse**: For command-line argument parsing
- **pathlib**: For cross-platform path handling
- **JSON**: For response formatting

## License

This application is part of the lineagentic-builder project.
