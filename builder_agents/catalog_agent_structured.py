"""
Structured Catalog Agent using OpenAI structured output and Pydantic models.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .base_structured import BaseStructuredAgent, Message

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
        ask_order = self.get_config_list("ask_order", ["catalog_type", "metadata_fields", "lineage_tracking", "discovery_enabled", "quality_metrics"])
        prompts = self.get_config_dict("prompts", {})
        completion_message = self.get_config("completion_message", "Catalog configuration captured.")
        
        prompt = f"""You are a data catalog agent. Your job is to help users configure catalog settings for their data product.

Required fields in order: {ask_order}

Available prompts:
{chr(10).join([f"- {field}: {prompts.get(field, f'What is the {field}?')}" for field in ask_order])}

Completion message: {completion_message}

CRITICAL: Always check the conversation context first!
- Review the current data product state to see what's already captured
- Check conversation history to understand what's been discussed
- NEVER ask for information that has already been provided
- Only ask for missing fields that haven't been captured yet

STATE CHECKING RULES:
- If "catalog" exists in data_product, check if it contains:
  * "catalog_type" - catalog type is configured
  * "metadata_fields" - metadata fields are configured
  * "lineage_tracking" - lineage tracking is configured
  * "discovery_enabled" - discovery is configured
  * "quality_metrics" - quality metrics are configured
  * "dashboards" - catalog dashboards are configured
- If ALL of these fields exist in catalog, catalog configuration is COMPLETE
- If user asks "what is next" and catalog is complete, provide completion message
- NEVER ask for catalog fields that are already configured

NATURAL LANGUAGE UNDERSTANDING:
- Users can say things naturally, not just with explicit keywords
- "catalog" = catalog_type
- "metadata" = metadata_fields
- "data dictionary" = metadata_fields
- "lineage" = lineage_tracking
- "data lineage" = lineage_tracking
- "discovery" = discovery_enabled
- "search" = discovery_enabled
- "quality metrics" = quality_metrics
- "data quality" = quality_metrics
- "dashboards" = dashboards

CATALOG COMPLETION DETECTION:
- If user provides catalog configuration and it's already captured, acknowledge and move to next step
- If user asks "what is next" and catalog is complete, provide completion message
- If user mentions specific catalog features and they're already configured, acknowledge completion

Your task:
1. First, analyze the conversation context to understand current progress
2. Extract any catalog configuration information from the user's message
3. Identify what catalog fields are still missing (only ask for uncaptured fields)
4. Provide a helpful response guiding the user to the next missing field
5. If all fields are complete, provide the completion message

IMPORTANT: Always provide clear examples in your responses to help users understand what you're asking for.

Respond with a JSON object containing:
- reply: Your response message (include examples when asking for information)
- confidence: Your confidence level (0.0 to 1.0)
- next_action: Suggested next action (e.g., "provide_catalog_type", "provide_metadata_fields", "complete")
- metadata: Any additional information
- extracted_data: Any catalog configuration data you extracted from the message
- missing_fields: List of catalog fields that are still missing

Be helpful and guide the user through the catalog configuration process step by step with clear examples, but never repeat questions for information already provided."""
        
        return prompt
    
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
            
            # Update state with extracted data
            if validated_output.extracted_data:
                data_product = state.setdefault("data_product", {})
                catalog_config = data_product.setdefault("catalog", {})
                catalog_config.update(validated_output.extracted_data)
            
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
