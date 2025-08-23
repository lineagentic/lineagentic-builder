"""
Structured Schema Contract Agent using OpenAI structured output and Pydantic models.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .base_structured import BaseStructuredAgent, Message

class SchemaInput(BaseModel):
    """Input model for schema contract agent."""
    message: str = Field(description="The user's message")
    role: str = Field(description="The role of the message sender")
    state: Dict[str, Any] = Field(description="Current conversation state")
    data_product: Dict[str, Any] = Field(default_factory=dict, description="Current data product specification")
    current_schema: List[Dict[str, Any]] = Field(default_factory=list, description="Current schema being built")

class SchemaOutput(BaseModel):
    """Output model for schema contract agent."""
    reply: str = Field(description="The response message to send to the user")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence level of the response")
    next_action: Optional[str] = Field(default=None, description="Suggested next action for the user")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    command_type: Optional[str] = Field(default=None, description="Type of command detected (output, field, fields_done, sla)")
    extracted_data: Dict[str, Any] = Field(default_factory=dict, description="Extracted data from the message")
    schema_updates: List[Dict[str, Any]] = Field(default_factory=list, description="Schema updates to apply")

class SchemaContractAgentStructured(BaseStructuredAgent):
    name = "schema_contract"
    
    def get_input_model(self) -> type[SchemaInput]:
        return SchemaInput
    
    def get_output_model(self) -> type[SchemaOutput]:
        return SchemaOutput
    
    def get_system_prompt(self) -> str:
        commands = self.get_config_dict("commands", {})
        
        prompt = f"""You are a data product schema contract agent. Your job is to help users define output interfaces, fields, and SLAs.

Available commands:
1. output: Define an output interface (e.g., "output:name=customer_profile_v1,type=table,sink=uc.analytics.customer_profile,freshness=15m")
2. field: Define a field (e.g., "field:name=customer_id,type=string,pk=true,pii=false")
3. fields:done: Complete the current schema
4. sla: Define SLAs (e.g., "sla:availability=99.9%,latency=10m")

Command configurations:
{chr(10).join([f"- {cmd}: {config.get('help', 'No help available')}" for cmd, config in commands.items()])}

Your task:
1. Detect the command type from the user's message
2. Extract relevant data from the message
3. Provide appropriate response based on the command
4. Suggest next actions

Respond with a JSON object containing:
- reply: Your response message
- confidence: Your confidence level (0.0 to 1.0)
- next_action: Suggested next action (e.g., "add_field", "define_sla", "complete")
- metadata: Any additional information
- command_type: Type of command detected
- extracted_data: Any data you extracted from the message
- schema_updates: Any schema updates to apply

Be helpful and guide the user through the schema definition process."""
        
        return prompt
    
    def extract_structured_input(self, message: Message, state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured input from message and state."""
        data_product = state.get("data_product", {})
        interfaces = data_product.get("interfaces", {})
        outputs = interfaces.get("outputs", [])
        current_schema = state.get("last_schema", [])
        
        return {
            "message": message.content,
            "role": message.role,
            "state": state,
            "data_product": data_product,
            "current_schema": current_schema
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
                    {"role": "user", "content": f"User message: {validated_input.message}\nCurrent data product: {validated_input.data_product}\nCurrent schema: {validated_input.current_schema}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            # Parse and validate response
            response_content = response.choices[0].message.content
            output_model = self.get_output_model()
            validated_output = output_model.model_validate_json(response_content)
            
            # Apply schema updates
            if validated_output.schema_updates:
                self._apply_schema_updates(state, validated_output)
            
            # Update state with extracted data
            if validated_output.extracted_data:
                data_product = state.setdefault("data_product", {})
                data_product.update(validated_output.extracted_data)
            
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
                "reply": f"I encountered an error processing your request: {str(e)}",
                "confidence": 0.0,
                "next_action": "help",
                "metadata": {"error": str(e)}
            }
    
    def _apply_schema_updates(self, state: Dict[str, Any], output: SchemaOutput):
        """Apply schema updates to the state."""
        command_type = output.command_type
        
        if command_type == "output":
            # Handle output command
            if output.extracted_data:
                data_product = state.setdefault("data_product", {})
                interfaces = data_product.setdefault("interfaces", {})
                outputs = interfaces.setdefault("outputs", [])
                
                output_config = output.extracted_data
                new_output = {
                    "name": output_config.get("name", "output1"),
                    "type": output_config.get("type", "table"),
                    "sink": output_config.get("sink", ""),
                    "freshness_slo": output_config.get("freshness", ""),
                    "schema": state.get("last_schema", [])
                }
                outputs.append(new_output)
        
        elif command_type == "field":
            # Handle field command
            if output.extracted_data:
                last_schema = state.setdefault("last_schema", [])
                field_config = output.extracted_data
                
                new_field = {
                    "name": field_config.get("name", "col"),
                    "type": field_config.get("type", "string"),
                    "pii": field_config.get("pii", False),
                    "primary_key": field_config.get("pk", False)
                }
                
                if new_field["pii"] and "classification" not in field_config:
                    new_field["classification"] = "personal"
                
                last_schema.append(new_field)
        
        elif command_type == "fields_done":
            # Clear temporary schema
            state.pop("last_schema", None)
        
        elif command_type == "sla":
            # Handle SLA command
            if output.extracted_data:
                data_product = state.setdefault("data_product", {})
                data_product["sla"] = output.extracted_data
