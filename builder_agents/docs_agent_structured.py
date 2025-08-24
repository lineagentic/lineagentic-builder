"""
Structured Docs Agent using OpenAI structured output and Pydantic models.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .base_structured import BaseStructuredAgent, Message

class DocsInput(BaseModel):
    """Input model for documentation agent."""
    message: str = Field(description="The user's message")
    conversation_context: str = Field(description="Current conversation context")
    current_state: Dict[str, Any] = Field(description="Current conversation state")

class DocsOutput(BaseModel):
    """Output model for docs agent."""
    reply: str = Field(description="The response message to send to the user")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence level of the response")
    next_action: Optional[str] = Field(default=None, description="Suggested next action for the user")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    extracted_data: Dict[str, Any] = Field(default_factory=dict, description="Extracted data from the message")
    missing_fields: List[str] = Field(default_factory=list, description="List of missing required fields")

class DocsAgentStructured(BaseStructuredAgent):
    name = "docs"
    
    def get_input_model(self) -> type[DocsInput]:
        return DocsInput
    
    def get_output_model(self) -> type[DocsOutput]:
        return DocsOutput
    
    def get_system_prompt(self) -> str:
        ask_order = self.get_config_list("ask_order", ["doc_type", "sections", "format", "audience", "artifacts"])
        prompts = self.get_config_dict("prompts", {})
        completion_message = self.get_config("completion_message", "Documentation configuration captured.")
        
        prompt = f"""You are a documentation agent. Your job is to help users configure documentation settings for their data product.

Required fields in order: {ask_order}

Available prompts:
{chr(10).join([f"- {field}: {prompts.get(field, f'What is the {field}?')}" for field in ask_order])}

Completion message: {completion_message}

CRITICAL: Always check the conversation context first!
- Review the current data product state to see what's already captured
- Check conversation history to understand what's been discussed
- NEVER ask for information that has already been provided
- Only ask for missing fields that haven't been captured yet

NATURAL LANGUAGE UNDERSTANDING:
- Users can say things naturally, not just with explicit keywords
- "documentation" = doc_type
- "docs" = doc_type
- "guide" = doc_type
- "sections" = sections
- "what to include" = sections
- "format" = format
- "file type" = format
- "audience" = audience
- "who is it for" = audience
- "artifacts" = artifacts
- "what to document" = artifacts

DOCUMENTATION TYPE EXTRACTION:
- "technical guide" = doc_type: "technical_guide"
- "user guide" = doc_type: "user_guide"
- "api documentation" = doc_type: "api_docs"
- "data dictionary" = doc_type: "data_dictionary"
- "runbook" = doc_type: "runbook"
- "comprehensive" = doc_type: "comprehensive"
- "all" = doc_type: "comprehensive"
- "everything" = doc_type: "comprehensive"

SECTION EXTRACTION:
- If user mentions specific sections, extract them immediately
- "Technical Guide, User Guide, API Documentation" = sections: ["Technical Guide", "User Guide", "API Documentation"]
- "Data Dictionary, Runbook" = sections: ["Data Dictionary", "Runbook"]
- "all sections" = sections: ["Technical Guide", "User Guide", "API Documentation", "Data Dictionary", "Runbook"]

Your task:
1. First, analyze the conversation context to understand current progress
2. Extract any documentation configuration information from the user's message
3. Identify what documentation fields are still missing (only ask for uncaptured fields)
4. Provide a helpful response guiding the user to the next missing field
5. If all fields are complete, provide the completion message

IMPORTANT RULES:
- If user says "technical guide", extract doc_type: "technical_guide" and sections: ["Technical Guide"]
- If user says "user guide", extract doc_type: "user_guide" and sections: ["User Guide"]
- If user says "api documentation", extract doc_type: "api_docs" and sections: ["API Documentation"]
- If user says "data dictionary", extract doc_type: "data_dictionary" and sections: ["Data Dictionary"]
- If user says "runbook", extract doc_type: "runbook" and sections: ["Runbook"]
- If user mentions multiple sections, extract all of them
- NEVER ask for the same field twice if it's already been provided
- CHECK THE CURRENT STATE FIRST - if a field is already set, don't ask for it again

IMPORTANT: Always provide clear examples in your responses to help users understand what you're asking for.

Respond with a JSON object containing:
- reply: Your response message (include examples when asking for information)
- confidence: Your confidence level (0.0 to 1.0)
- next_action: Suggested next action (e.g., "provide_doc_type", "provide_sections", "complete")
- metadata: Any additional information
- extracted_data: Any documentation configuration data you extracted from the message
- missing_fields: List of documentation fields that are still missing

Be helpful and guide the user through the documentation configuration process step by step with clear examples, but never repeat questions for information already provided."""
        
        return prompt
    
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
            input_data = DocsInput(
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
            validated_output = DocsOutput.model_validate_json(response_content)
            
            # Update conversation state (avoid duplicates)
            if validated_output.extracted_data:
                data_product = state.get("data_product", {})
                if "documentation" not in data_product:
                    data_product["documentation"] = {}
                documentation = data_product["documentation"]
                for key, value in validated_output.extracted_data.items():
                    # Only update if value is different or doesn't exist
                    if key not in documentation or documentation[key] != value:
                        documentation[key] = value
                state["data_product"] = data_product
            
            # Check if all required fields are complete
            ask_order = self.get_config_list("ask_order", ["doc_type", "sections", "format", "audience", "artifacts"])
            documentation = state.get("data_product", {}).get("documentation", {})
            
            # Check if all fields are present
            all_fields_complete = all(
                field in documentation and documentation[field] 
                for field in ask_order
            )
            
            if all_fields_complete:
                completion_message = self.get_config("completion_message", "Documentation configuration captured.")
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
            documentation = state.get("data_product", {}).get("documentation", {})
            
            # Create a helpful error message that maintains context
            error_message = f"I encountered an issue processing your message: {str(e)}. "
            
            # Check what we have so far and provide context
            if documentation:
                error_message += "Here's what I have so far:\n"
                for key, value in documentation.items():
                    error_message += f"- {key}: {value}\n"
                error_message += "\nPlease continue providing the missing information."
            else:
                error_message += "Let me help you start defining your data product documentation. What type of documentation do you need?"
            
            return {
                "reply": error_message,
                "confidence": 0.0,
                "next_action": "retry",
                "metadata": {"error": str(e), "state_preserved": True},
                "extracted_data": {},
                "missing_fields": []
            }
