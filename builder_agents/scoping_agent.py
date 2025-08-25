"""
Structured Scoping Agent using OpenAI structured output and Pydantic models.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .base import BaseStructuredAgent, Message

class ScopingInput(BaseModel):
    """Input model for scoping agent."""
    message: str = Field(description="The user's message")
    conversation_context: str = Field(description="Current conversation context")
    current_state: Dict[str, Any] = Field(description="Current conversation state")

class ScopingOutput(BaseModel):
    """Output model for scoping agent."""
    reply: str = Field(description="The response message to send to the user")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence level of the response")
    next_action: Optional[str] = Field(default=None, description="Suggested next action for the user")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    extracted_data: Dict[str, Any] = Field(default_factory=dict, description="Extracted data from the message")
    missing_fields: List[str] = Field(default_factory=list, description="List of missing required fields")

class ScopingAgentStructured(BaseStructuredAgent):
    name = "scoping"
    
    def get_input_model(self) -> type[ScopingInput]:
        return ScopingInput
    
    def get_output_model(self) -> type[ScopingOutput]:
        return ScopingOutput
    
    def get_system_prompt(self) -> str:
        from .scoping_agent_instructions import SCOPING_AGENT_SYSTEM_PROMPT
        return SCOPING_AGENT_SYSTEM_PROMPT
    
    def extract_structured_input(self, message: Message, state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured input from message and state."""
        return {
            "message": message.content,
            "role": message.role,
            "state": state,
            "data_product": state.get("data_product", {})
        }
    
    async def handle_async(self, state: Dict[str, Any], message: Message) -> Dict[str, Any]:
        """Handle message using OpenAI structured output."""
        try:
            # Build conversation context
            conversation_context = self._build_conversation_context(state)
            
            # Create input for the agent
            input_data = ScopingInput(
                message=message.content,
                conversation_context=conversation_context,
                current_state=state
            )
            
            # Get system prompt
            system_prompt = self.get_system_prompt()
            
            # Call OpenAI with structured output using the base class method
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Conversation Context:\n{conversation_context}\n\nCurrent Message: {message.content}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            # Parse the response
            response_content = response.choices[0].message.content
            validated_output = ScopingOutput.model_validate_json(response_content)
            
            # Update conversation state (avoid duplicates)
            if validated_output.extracted_data:
                data_product = state.get("data_product", {})
                for key, value in validated_output.extracted_data.items():
                    # Only update if value is different or doesn't exist
                    if key not in data_product or data_product[key] != value:
                        data_product[key] = value
                state["data_product"] = data_product
            
            # Check if all required fields are complete
            ask_order = self.get_config_list("ask_order", ["name", "domain", "owner", "purpose", "upstreams"])
            data_product = state.get("data_product", {})
            
            # Check if all fields are present
            all_fields_complete = all(
                field in data_product and data_product[field] 
                for field in ask_order
            )
            
            if all_fields_complete:
                completion_message = self.get_config("completion_message", "Scope captured.")
                validated_output.reply = completion_message
                validated_output.next_action = "complete"
            
            # Enhance reply with examples
            reply = self.enhance_reply_with_example(validated_output.reply, validated_output.next_action)
            
            return {
                "reply": reply,
                "confidence": validated_output.confidence,
                "next_action": validated_output.next_action,
                "metadata": validated_output.metadata,
                "extracted_data": validated_output.extracted_data,
                "missing_fields": validated_output.missing_fields
            }
            
        except Exception as e:
            # Preserve the current state even when there's an error
            data_product = state.get("data_product", {})
            
            # Create a helpful error message that maintains context
            error_message = f"I encountered an issue processing your message: {str(e)}. "
            
            # Check what we have so far and provide context
            if data_product:
                error_message += "Here's what I have so far:\n"
                for key, value in data_product.items():
                    error_message += f"- {key}: {value}\n"
                error_message += "\nPlease continue providing the missing information."
            else:
                error_message += "Let me help you start defining your data product. What would you like to call it?"
            
            return {
                "reply": error_message,
                "confidence": 0.0,
                "next_action": "retry",
                "metadata": {"error": str(e), "state_preserved": True},
                "extracted_data": {},
                "missing_fields": []
            }
