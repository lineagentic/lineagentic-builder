# Data Product Scoping Agent

This agent provides comprehensive data product scoping capabilities using the MCP (Model Context Protocol) server infrastructure.

## Overview

The Data Product Scoping Agent is designed to help define and scope data products by:
- Analyzing user requirements
- Extracting key data product information
- Validating completeness of scope
- Providing structured documentation

## Architecture

The agent uses:
- **`dp_builder_server.py`** - MCP server that exposes the scoping agent as tools
- **`mcp_params.py`** - Configuration for the MCP server connection
- **`data_product_scoping_agent.py`** - Main agent implementation

## Required Fields

The agent extracts the following required fields for a complete data product scope:
- **name**: The name of the data product
- **domain**: The business domain or area
- **owner**: The person or team responsible
- **purpose**: The business purpose and value proposition
- **upstreams**: Data sources and dependencies

## Setup

1. **Install Dependencies**
   ```bash
   pip install openai python-dotenv
   ```

2. **Set Environment Variables**
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   ```

3. **Ensure MCP Server is Available**
   The agent expects the `dp_builder_server.py` to be available in the `dp_server/` directory.

## Usage

### Basic Usage

```python
import asyncio
from data_product_scoping_agent import DataProductScopingAgent

async def main():
    # Create the agent directly
    agent = DataProductScopingAgent(
        agent_name="MyDataProduct",
        user_requirements="Your requirements here...",
        model_name="gpt-4o-mini"
    )
    
    # Run the agent
    result = await agent.run()
    print(result)

# Run the agent
asyncio.run(main())
```

### Example Usage

See `example_usage.py` for a complete working example.

## Agent Workflow

The agent follows this comprehensive workflow:

1. **Initial Scoping Analysis**
   - Analyzes user requirements using the scoping_agent() MCP tool
   - Extracts initial data product information

2. **Iterative Refinement**
   - Identifies missing or unclear information
   - Makes additional calls to refine the scope
   - Continues until all required fields are complete

3. **Validation and Confirmation**
   - Reviews current data product state
   - Verifies completeness of all required fields
   - Fills any remaining gaps

4. **Final Documentation**
   - Provides comprehensive summary
   - Includes all extracted information
   - Offers next steps recommendations

## MCP Tools Used

The agent interacts with these MCP tools:
- `scoping_agent()` - Main tool for data product analysis
- `get_conversation_state()` - Review current state
- `reset_conversation()` - Start fresh if needed

## Error Handling

The agent includes comprehensive error handling:
- Validates OpenAI API key availability
- Handles MCP server connection issues
- Provides clear error messages
- Preserves conversation state on errors

## Configuration

### Model Selection
You can specify different models:
- `gpt-4o-mini` (default)
- `gpt-4o`
- `gpt-4-turbo`
- Any other OpenAI model

### Custom Model Function
You can provide a custom model loading function:
```python
def my_model_loader(model_name):
    # Your custom model loading logic
    return model

agent = DataProductScopingAgent(
    agent_name="MyAgent",
    user_requirements="...",
    get_model_func=my_model_loader
)
```

## Output Format

The agent returns structured output containing:
- Extracted data product information
- Confidence scores
- Next action recommendations
- Metadata and conversation history

## Troubleshooting

### Common Issues

1. **OPENAI_API_KEY not set**
   - Ensure the environment variable is properly set
   - Check for typos in the variable name

2. **MCP Server not found**
   - Verify `dp_builder_server.py` exists in `dp_server/`
   - Check that `mcp_params.py` is properly configured

3. **Import errors**
   - Ensure all dependencies are installed
   - Check Python path includes the project root

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

To extend the agent:
1. Modify the instruction functions in `data_product_scoping_agent.py`
2. Add new MCP tools to `dp_builder_server.py`
3. Update the workflow in `comprehensive_scoping_instructions()`

## License

This project is part of the LineAgentic Builder framework.
