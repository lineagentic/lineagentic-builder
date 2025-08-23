"""
Structured Provisioning Agent using OpenAI structured output.
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from .base_structured import BaseStructuredAgent, Message

class ProvisioningInput(BaseModel):
    """Input model for provisioning agent."""
    message: str = Field(description="The user message to process")
    role: str = Field(description="The role of the message sender")
    state: Dict[str, Any] = Field(description="Current state of the data product")

class ProvisioningOutput(BaseModel):
    """Output model for provisioning agent."""
    reply: str = Field(description="The response message to send to the user")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence level of the response")
    next_action: Optional[str] = Field(default=None, description="Suggested next action for the user")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class ProvisioningAgentStructured(BaseStructuredAgent):
    """Structured provisioning agent for deployment and infrastructure."""
    
    name = "provisioning"
    
    def get_input_model(self):
        return ProvisioningInput
    
    def get_output_model(self):
        return ProvisioningOutput
    
    def get_system_prompt(self) -> str:
        return """You are a provisioning agent responsible for deploying data products and managing infrastructure.

Your responsibilities include:
1. Processing deploy commands (e.g., "deploy:dev", "deploy:staging", "deploy:prod")
2. Writing data product specifications to files
3. Setting up infrastructure and CI/CD pipelines
4. Providing deployment status and next steps

When a user says "deploy:env", you should:
1. Extract the environment (dev/staging/prod)
2. Write the current data product spec to data-product.yaml
3. Write the policy pack to policies/policy-pack.yaml
4. Provide a success message with next steps

Always respond with high confidence when the request is clear.
Suggest appropriate next actions like "Open a PR to run CI" or "Review the generated files".
"""
