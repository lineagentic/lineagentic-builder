"""
Structured Observability Agent using OpenAI structured output.
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from .base_structured import BaseStructuredAgent, Message

class ObservabilityInput(BaseModel):
    """Input model for observability agent."""
    message: str = Field(description="The user message to process")
    role: str = Field(description="The role of the message sender")
    state: Dict[str, Any] = Field(description="Current state of the data product")

class ObservabilityOutput(BaseModel):
    """Output model for observability agent."""
    reply: str = Field(description="The response message to send to the user")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence level of the response")
    next_action: Optional[str] = Field(default=None, description="Suggested next action for the user")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class ObservabilityAgentStructured(BaseStructuredAgent):
    """Structured observability agent for monitoring and alerting."""
    
    name = "observability"
    
    def get_input_model(self):
        return ObservabilityInput
    
    def get_output_model(self):
        return ObservabilityOutput
    
    def get_system_prompt(self) -> str:
        return """You are an observability agent responsible for setting up monitoring, alerting, and observability for data products.

Your responsibilities include:
1. Setting up monitoring dashboards
2. Configuring alerting rules and thresholds
3. Implementing logging and tracing
4. Creating SLA monitoring
5. Setting up data quality checks and alerts

When setting up observability, you should:
1. Define key metrics and KPIs
2. Set up appropriate alerting thresholds
3. Configure monitoring dashboards
4. Implement data quality checks
5. Set up incident response procedures

Always respond with high confidence when the observability request is clear.
Suggest next actions like "Review the monitoring setup" or "Configure additional alerts".
"""
