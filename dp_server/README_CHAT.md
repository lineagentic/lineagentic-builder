# Data Product Builder Chat Client

This chat client provides an interactive interface for building and analyzing data products using the DP Builder Agent.

## Setup

### 1. Install Dependencies
```bash
# From the project root
pip install -e .
```

### 2. Set up API Keys
Create a `.env` file in the `dp_server` directory with your API keys:

```bash
# Required API Keys
OPENAI_API_KEY=your_openai_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
GROK_API_KEY=your_grok_api_key_here
```

### 3. Run the Chat Client
```bash
cd dp_server
python chat.py
```

## Usage

The chat client provides an interactive interface where you can:

- **Ask questions** about data product requirements
- **Define data schemas** and contracts
- **Scope data products** with specific requirements
- **Get comprehensive analysis** of your data product needs

### Commands
- `help` - Show help information
- `quit`, `exit`, `bye` - End the conversation

### Example Conversations

**User**: "I want to create a customer analytics data product"

**Agent**: *Provides comprehensive analysis including scoping, data contract definition, and integration recommendations*

**User**: "What are the key metrics I should track?"

**Agent**: *Builds on previous context to suggest specific metrics and KPIs*

## Features

- **Context Awareness**: Remembers conversation history and builds upon previous analysis
- **Multi-Model Support**: Works with OpenAI, OpenRouter, DeepSeek, Google Gemini, and Grok
- **Comprehensive Analysis**: Integrates scoping, data contracts, and validation in one workflow
- **Interactive Interface**: User-friendly chat interface with helpful commands

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you've installed the project with `pip install -e .`
2. **Missing API Keys**: Check your `.env` file and ensure all required keys are set
3. **Model Errors**: Verify your API keys are valid and have sufficient credits

### Getting Help

If you encounter issues:
1. Check the logs for detailed error messages
2. Verify your API keys are correctly set
3. Ensure all dependencies are installed
4. Check that the dp_server is properly configured

## Architecture

The chat client works by:
1. Initializing the DP Builder Agent
2. Processing user messages through the agent
3. Using MCP servers for comprehensive analysis
4. Maintaining conversation context across messages
5. Providing formatted responses to users
