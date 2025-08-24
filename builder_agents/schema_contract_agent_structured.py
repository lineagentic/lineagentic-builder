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
        ask_order = self.get_config_list("ask_order", ["output_name", "output_type", "sink_location", "freshness", "fields"])
        prompts = self.get_config_dict("prompts", {})
        completion_message = self.get_config("completion_message", "Schema contract captured.")
        field_patterns = self.get_config_list("field_patterns", [])
        
        prompt = f"""You are a data product schema contract agent. Your job is to help users configure output interfaces and schemas for their data product.

Required fields in order: {ask_order}

Available prompts:
{chr(10).join([f"- {field}: {prompts.get(field, f'What is the {field}?')}" for field in ask_order])}

Completion message: {completion_message}

Field parsing patterns:
{chr(10).join([f"- {pattern}" for pattern in field_patterns])}

CRITICAL: Always check the conversation context first!
- Review the current data product state to see what's already captured
- Check conversation history to understand what's been discussed
- NEVER ask for information that has already been provided
- Only ask for missing fields that haven't been captured yet

NATURAL LANGUAGE UNDERSTANDING:
- Users can say things naturally, not just with explicit keywords
- "data structure" = fields
- "columns" = fields
- "data types" = fields
- "table structure" = fields
- "output table" = output_name
- "where to store" = sink_location
- "how often" = freshness
- "update frequency" = freshness

Your task:
1. First, analyze the conversation context to understand current progress
2. Extract any schema configuration information from the user's message
3. Parse field definitions from natural language (e.g., "customer_id string pk, email string pii")
4. Identify what schema fields are still missing (only ask for uncaptured fields)
5. Provide a helpful response guiding the user to the next missing field
6. If all fields are complete, provide the completion message

When parsing fields, look for patterns like:
- "field_name data_type [pk] [pii] [description]"
- Examples: "customer_id string pk", "email string pii", "name string", "age integer"
- Data types: string, integer, float, boolean, date, timestamp
- Flags: pk (primary key), pii (personal data), required (not null)

IMPORTANT: Always provide clear examples in your responses to help users understand what you're asking for.

Respond with a JSON object containing:
- reply: Your response message (include examples when asking for information)
- confidence: Your confidence level (0.0 to 1.0)
- next_action: Suggested next action (e.g., "provide_output_name", "provide_output_type", "complete")
- metadata: Any additional information
- extracted_data: Any schema configuration data you extracted from the message
- missing_fields: List of schema fields that are still missing
- parsed_fields: List of parsed field objects with name, type, pii, pk, required flags

Be helpful and guide the user through the schema configuration process step by step with clear examples, but never repeat questions for information already provided."""
        
        return prompt
    
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
