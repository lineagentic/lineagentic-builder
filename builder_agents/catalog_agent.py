"""
Structured Catalog Agent using OpenAI structured output and Pydantic models.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .base import BaseStructuredAgent, Message

class CatalogInput(BaseModel):
    """Input model for catalog agent."""
    conversation_context: str = Field(description="Full conversation context including history")
    current_state: Dict[str, Any] = Field(description="Current conversation state")

class CatalogOutput(BaseModel):
    """Output model for catalog agent."""
    reply: str = Field(description="The response message to send to the user")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence level of the response")
    next_action: Optional[str] = Field(default=None, description="Suggested next action for the user")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    extracted_data: Dict[str, Any] = Field(default_factory=dict, description="Extracted data from the message")
    missing_fields: List[str] = Field(default_factory=list, description="List of missing required fields")

class CatalogAgentStructured(BaseStructuredAgent):
    name = "catalog"
    
    def get_input_model(self) -> type[CatalogInput]:
        return CatalogInput
    
    def get_output_model(self) -> type[CatalogOutput]:
        return CatalogOutput
    
    def get_system_prompt(self) -> str:
        from .catalog_agent_instructions import CATALOG_AGENT_SYSTEM_PROMPT
        return CATALOG_AGENT_SYSTEM_PROMPT
    
    async def handle_async(self, state: Dict[str, Any], message: Message) -> Dict[str, Any]:
        """Handle message using OpenAI structured output."""
        try:
            # Build conversation context using base class method
            conversation_context = self._build_conversation_context(state, message)
            
            # Extract structured input
            input_data = {
                "conversation_context": conversation_context,
                "current_state": state
            }
            
            # Validate input using Pydantic model
            input_model = self.get_input_model()
            validated_input = input_model(**input_data)
            
            # Get system prompt
            system_prompt = self.get_system_prompt()
            
            # Call OpenAI with structured output
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": conversation_context}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            # Parse and validate response
            response_content = response.choices[0].message.content
            output_model = self.get_output_model()
            validated_output = output_model.model_validate_json(response_content)
            
            # Update state with extracted data (avoid duplicates)
            if validated_output.extracted_data:
                data_product = state.setdefault("data_product", {})
                catalog_config = data_product.setdefault("catalog", {})
                for key, value in validated_output.extracted_data.items():
                    # Only update if value is different or doesn't exist
                    if key not in catalog_config or catalog_config[key] != value:
                        catalog_config[key] = value
            
            # Convert to dict format expected by the system
            return {
                "reply": validated_output.reply,
                "confidence": validated_output.confidence,
                "next_action": validated_output.next_action,
                "metadata": validated_output.metadata
            }
            
        except Exception as e:
            print(f"Error in structured catalog agent: {e}")
            # Preserve existing state and provide context-aware error message
            data_product = state.get("data_product", {})
            catalog_config = data_product.get("catalog", {})
            
            if catalog_config:
                return {
                    "reply": f"I encountered an error processing your catalog request, but I can see you have catalog configuration already set up. Could you please clarify what specific aspect of catalog or metadata management you'd like to address?",
                    "confidence": 0.0,
                    "next_action": "help",
                    "metadata": {"error": str(e), "existing_config": True}
                }
            else:
                return {
                    "reply": f"I encountered an error processing your catalog request: {str(e)}. Let me help you set up the data catalog and metadata management configuration for your data product.",
                    "confidence": 0.0,
                    "next_action": "help",
                    "metadata": {"error": str(e)}
                }
