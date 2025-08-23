"""
Structured Catalog Agent using OpenAI structured output.
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from .base_structured import BaseStructuredAgent, Message

class CatalogInput(BaseModel):
    """Input model for catalog agent."""
    message: str = Field(description="The user message to process")
    role: str = Field(description="The role of the message sender")
    state: Dict[str, Any] = Field(description="Current state of the data product")

class CatalogOutput(BaseModel):
    """Output model for catalog agent."""
    reply: str = Field(description="The response message to send to the user")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence level of the response")
    next_action: Optional[str] = Field(default=None, description="Suggested next action for the user")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class CatalogAgentStructured(BaseStructuredAgent):
    """Structured catalog agent for data cataloging and metadata management."""
    
    name = "catalog"
    
    def get_input_model(self):
        return CatalogInput
    
    def get_output_model(self):
        return CatalogOutput
    
    def get_system_prompt(self) -> str:
        return """You are a catalog agent responsible for managing data catalogs and metadata for data products.

Your responsibilities include:
1. Registering data products in data catalogs
2. Managing metadata and lineage information
3. Creating data dictionaries
4. Setting up data discovery and search capabilities
5. Maintaining data quality metrics

When cataloging a data product, you should:
1. Extract key metadata from the data product specification
2. Create comprehensive data dictionaries
3. Set up lineage tracking
4. Configure search and discovery features
5. Ensure compliance with data governance policies

Always respond with high confidence when the cataloging request is clear.
Suggest next actions like "Review the catalog entry" or "Set up additional metadata fields".
"""
