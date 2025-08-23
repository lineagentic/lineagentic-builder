"""
Structured Documentation Agent using OpenAI structured output.
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from .base_structured import BaseStructuredAgent, Message

class DocsInput(BaseModel):
    """Input model for documentation agent."""
    message: str = Field(description="The user message to process")
    role: str = Field(description="The role of the message sender")
    state: Dict[str, Any] = Field(description="Current state of the data product")

class DocsOutput(BaseModel):
    """Output model for documentation agent."""
    reply: str = Field(description="The response message to send to the user")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence level of the response")
    next_action: Optional[str] = Field(default=None, description="Suggested next action for the user")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class DocsAgentStructured(BaseStructuredAgent):
    """Structured documentation agent for generating documentation."""
    
    name = "docs"
    
    def get_input_model(self):
        return DocsInput
    
    def get_output_model(self):
        return DocsOutput
    
    def get_system_prompt(self) -> str:
        return """You are a documentation agent responsible for generating comprehensive documentation for data products.

Your responsibilities include:
1. Creating README files with usage instructions
2. Generating API documentation
3. Writing technical specifications
4. Creating user guides and tutorials
5. Documenting data schemas and transformations

When generating documentation, you should:
1. Include clear usage examples
2. Document all fields and their purposes
3. Provide troubleshooting guides
4. Include contact information and support details
5. Follow consistent formatting and style

Always respond with high confidence when the documentation request is clear.
Suggest next actions like "Review the generated documentation" or "Add more specific examples".
"""
