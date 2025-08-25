"""
Structured Schema Contract Agent using OpenAI structured output and Pydantic models.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .base import BaseStructuredAgent, Message

class SchemaInput(BaseModel):
    """Input model for schema contract agent."""
    message: str = Field(description="The user's message")
    role: str = Field(description="The role of the message sender")
    state: Dict[str, Any] = Field(description="Current conversation state")
    data_product: Dict[str, Any] = Field(default_factory=dict, description="Current data product specification")

class SchemaOutput(BaseModel):
    """Output model for schema contract agent."""
    reply: str = Field(description="The response message to send to the user")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence level of the response")
    next_action: Optional[str] = Field(default=None, description="Suggested next action for the user")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    extracted_data: Dict[str, Any] = Field(default_factory=dict, description="Extracted data from the message")
    missing_fields: List[str] = Field(default_factory=list, description="List of missing required fields")
    parsed_fields: List[Dict[str, Any]] = Field(default_factory=list, description="Parsed field definitions")

class SchemaContractAgentStructured(BaseStructuredAgent):
    name = "schema_contract"
    
    def get_input_model(self) -> type[SchemaInput]:
        return SchemaInput
    
    def get_output_model(self) -> type[SchemaOutput]:
        return SchemaOutput
    
    def get_system_prompt(self) -> str:
        from .schema_contract_agent_instructions import SCHEMA_CONTRACT_AGENT_SYSTEM_PROMPT
        return SCHEMA_CONTRACT_AGENT_SYSTEM_PROMPT
    
    def extract_structured_input(self, message: Message, state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured input from message and state."""
        return {
            "message": message.content,
            "role": message.role,
            "state": state,
            "data_product": state.get("data_product", {})
        }
    
    def handle(self, state: Dict[str, Any], message: Message) -> Dict[str, Any]:
        """Handle message using OpenAI structured output."""
        try:
            # Extract structured input
            input_data = self.extract_structured_input(message, state)
            
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
                    {"role": "user", "content": f"User message: {validated_input.message}\nCurrent data product: {validated_input.data_product}"}
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
                for key, value in validated_output.extracted_data.items():
                    # Only update if value is different or doesn't exist
                    if key not in data_product or data_product[key] != value:
                        data_product[key] = value
            
            # Update state with parsed fields (avoid duplicates)
            if validated_output.parsed_fields:
                data_product = state.setdefault("data_product", {})
                interfaces = data_product.setdefault("interfaces", {})
                outputs = interfaces.setdefault("outputs", [])
                
                # Add fields to the current output or create a new one
                if outputs:
                    current_output = outputs[-1]
                    schema = current_output.setdefault("schema", [])
                    
                    # Add fields without duplicates
                    for new_field in validated_output.parsed_fields:
                        field_name = new_field.get("name")
                        existing_field = next((f for f in schema if f.get("name") == field_name), None)
                        
                        if not existing_field:
                            # Add new field
                            schema.append(new_field)
                        else:
                            # Update existing field with new information (merge)
                            existing_field.update(new_field)
                else:
                    # Create a default output if none exists
                    new_output = {
                        "name": "output1",
                        "type": "table",
                        "schema": validated_output.parsed_fields
                    }
                    outputs.append(new_output)
            
            # Convert to dict format expected by the system
            return {
                "reply": validated_output.reply,
                "confidence": validated_output.confidence,
                "next_action": validated_output.next_action,
                "metadata": validated_output.metadata
            }
            
        except Exception as e:
            print(f"Error in structured schema agent: {e}")
            # Fallback to simple response
            return {
                "reply": f"I encountered an error processing your schema request: {str(e)}",
                "confidence": 0.0,
                "next_action": "help",
                "metadata": {"error": str(e)}
            }
