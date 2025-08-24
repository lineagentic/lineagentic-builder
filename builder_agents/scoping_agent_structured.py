"""
Structured Scoping Agent using OpenAI structured output and Pydantic models.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .base_structured import BaseStructuredAgent, Message

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
        ask_order = self.get_config_list("ask_order", ["name", "domain", "owner", "purpose", "upstreams"])
        prompts = self.get_config_dict("prompts", {})
        completion_message = self.get_config("completion_message", "Scope captured.")
        
        prompt = f"""You are a data product scoping agent. Your job is to help users define the basic scope of their data product.

Required fields in order: {ask_order}

Available prompts:
{chr(10).join([f"- {field}: {prompts.get(field, f'What is the {field}?')}" for field in ask_order])}

Completion message: {completion_message}

CRITICAL: Always check the conversation context first!
- Review the current data product state to see what's already captured
- Check conversation history to understand what's been discussed
- NEVER ask for information that has already been provided
- Only ask for missing fields that haven't been captured yet
- When user provides upstream sources (like "billing.stripes"), extract and store them properly

NATURAL LANGUAGE UNDERSTANDING:
- Users can say things naturally, not just with explicit keywords
- "upstream source" = upstreams field
- "data source" = upstreams field  
- "where data comes from" = upstreams field
- "product name" = name field
- "business domain" = domain field
- "who owns it" = owner field
- "what's the purpose" = purpose field

EXTRACTION RULES:
- ALWAYS extract email addresses when provided (e.g., "mm@gmail.com" → owner: "mm@gmail.com")
- ALWAYS extract team IDs when provided (e.g., "team:data-engineering" → owner: "team:data-engineering")
- ALWAYS extract domain names when provided (e.g., "sales" → domain: "sales")
- ALWAYS extract product names when provided (e.g., "customr-44" → name: "customr-44")
- ALWAYS extract upstream sources when provided (e.g., "crm.ff" → upstreams: ["crm.ff"])

UPSTREAM SOURCE EXTRACTION:
- Look for ANY mention of data sources in the message
- Common patterns: "crm.ff", "crm.custom", "crm.tt", "billing.stripe", "web.events"
- Extract ALL sources mentioned, even if they seem incomplete
- If user says "source is crm.tt", extract "crm.tt" as upstream source
- If user says "crm.ff", extract "crm.ff" as upstream source
- If user says "crm.custom", extract "crm.custom" as upstream source
- Combine multiple sources into a list: ["crm.ff", "crm.custom", "crm.tt"]

STATE CHECKING RULES:
- BEFORE asking for any field, check if it's already in the current data_product state
- If a field is already present in the state, DO NOT ask for it again
- If the user provides new information, extract it and update the state
- Only ask for fields that are actually missing from the current state

Your task:
1. First, analyze the conversation context to understand current progress
2. Check what's already in the data_product state - DO NOT ask for fields that are already there
3. Extract any information from the user's message (be thorough with natural language!)
4. Identify what fields are still missing (only ask for uncaptured fields)
5. Provide a helpful response guiding the user to the next missing field
6. If all fields are complete, provide the completion message

IMPORTANT RULES:
- If user mentions upstream sources (e.g., "crm.ff", "crm.custom", "crm.tt"), extract them as "upstreams" field
- If user says "no" to additional sources, treat current upstreams as complete
- Always provide clear examples in your responses
- Never ask for the same field twice if it's already been provided
- Understand natural language variations of field names
- ALWAYS extract email addresses, team IDs, domain names, and product names when they appear in the message
- If the user provides an email address like "mm@gmail.com", immediately extract it as the owner
- CHECK THE CURRENT STATE FIRST - if owner is already set, don't ask for it again
- BE THOROUGH in extracting upstream sources - look for ANY mention of data sources

Respond with a JSON object containing:
- reply: Your response message (include examples when asking for information)
- confidence: Your confidence level (0.0 to 1.0)
- next_action: Suggested next action (e.g., "provide_domain", "provide_owner", "complete")
- metadata: Any additional information
- extracted_data: Any data you extracted from the message (be thorough!)
- missing_fields: List of fields that are still missing

Be helpful and guide the user through the scoping process step by step with clear examples, but never repeat questions for information already provided."""
        
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
