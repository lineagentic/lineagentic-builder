"""
Structured Policy Agent using OpenAI structured output and Pydantic models.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .base_structured import BaseStructuredAgent, Message

class PolicyInput(BaseModel):
    """Input model for policy agent."""
    message: str = Field(description="The user's message")
    conversation_context: str = Field(description="Current conversation context")
    current_state: Dict[str, Any] = Field(description="Current conversation state")

class PolicyOutput(BaseModel):
    """Output model for policy agent."""
    reply: str = Field(description="The response message to send to the user")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence level of the response")
    next_action: Optional[str] = Field(default=None, description="Suggested next action for the user")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    extracted_data: Dict[str, Any] = Field(default_factory=dict, description="Extracted data from the message")
    missing_fields: List[str] = Field(default_factory=list, description="List of missing required fields")
    parsed_policies: Dict[str, Any] = Field(default_factory=dict, description="Parsed policy definitions")

class PolicyAgentStructured(BaseStructuredAgent):
    name = "policy"
    
    def get_input_model(self) -> type[PolicyInput]:
        return PolicyInput
    
    def get_output_model(self) -> type[PolicyOutput]:
        return PolicyOutput
    
    def get_system_prompt(self) -> str:
        ask_order = self.get_config_list("ask_order", ["access_control", "data_masking", "quality_gates", "retention_policy", "evaluation_points"])
        prompts = self.get_config_dict("prompts", {})
        completion_message = self.get_config("completion_message", "Policy configuration captured.")
        policy_patterns = self.get_config_list("policy_patterns", [])
        
        prompt = f"""You are a data product policy agent. Your job is to help users configure data governance policies for their data product.

Required fields in order: {ask_order}

Available prompts:
{chr(10).join([f"- {field}: {prompts.get(field, f'What is the {field}?')}" for field in ask_order])}

Completion message: {completion_message}

Policy parsing patterns:
{chr(10).join([f"- {pattern}" for pattern in policy_patterns])}

CRITICAL: Always check the conversation context first!
- Review the current data product state to see what's already captured
- Check conversation history to understand what's been discussed
- NEVER ask for information that has already been provided
- Only ask for missing fields that haven't been captured yet

NATURAL LANGUAGE UNDERSTANDING:
- Users can say things naturally, not just with explicit keywords
- "access control" = access_control
- "who can access" = access_control
- "permissions" = access_control
- "data masking" = data_masking
- "hide sensitive data" = data_masking
- "quality gates" = quality_gates
- "data quality" = quality_gates
- "retention" = retention_policy
- "how long to keep" = retention_policy
- "when to check" = evaluation_points

NEGATIVE RESPONSE HANDLING:
- "no masking required" = data_masking: "none"
- "no rules" = data_masking: "none"
- "no masking" = data_masking: "none"
- "no access control" = access_control: "none"
- "no quality gates" = quality_gates: "none"
- "no retention policy" = retention_policy: "none"
- "yes no masking required" = data_masking: "none"
- "there is no rule" = data_masking: "none"
- "i am ok" = data_masking: "none"

Your task:
1. First, analyze the conversation context to understand current progress
2. Extract any policy configuration information from the user's message
3. Parse policy definitions from natural language (e.g., "allow analysts and engineers", "mask email and phone")
4. Identify what policy fields are still missing (only ask for uncaptured fields)
5. Provide a helpful response guiding the user to the next missing field
6. If all fields are complete, provide the completion message

When parsing policies, look for patterns like:
- Access control: "allow role1, role2" or "deny role1, role2"
- Data masking: "mask column1, column2" or "mask email for role1"
- Quality gates: "column1 not null", "column2 unique", "column3 pattern"
- Retention: "delete after X days", "archive after Y years"
- Negative responses: "no masking required", "no rules", "none needed"

IMPORTANT: Always provide clear examples in your responses to help users understand what you're asking for.

IMPORTANT RULES:
- If user says "no masking required", extract data_masking: "none"
- If user says "no rules", extract data_masking: "none"
- If user says "there is no rule", extract data_masking: "none"
- If user says "i am ok", extract data_masking: "none"
- NEVER ask for the same field twice if it's already been provided
- CHECK THE CURRENT STATE FIRST - if a field is already set, don't ask for it again

Respond with a JSON object containing:
- reply: Your response message (include examples when asking for information)
- confidence: Your confidence level (0.0 to 1.0)
- next_action: Suggested next action (e.g., "provide_access_control", "provide_data_masking", "complete")
- metadata: Any additional information
- extracted_data: Any policy configuration data you extracted from the message
- missing_fields: List of policy fields that are still missing
- parsed_policies: Parsed policy objects with access, masking, quality, retention rules

Be helpful and guide the user through the policy configuration process step by step with clear examples, but never repeat questions for information already provided."""
        
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
            input_data = PolicyInput(
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
            validated_output = PolicyOutput.model_validate_json(response_content)
            
            # Update conversation state (avoid duplicates)
            if validated_output.extracted_data:
                data_product = state.get("data_product", {})
                for key, value in validated_output.extracted_data.items():
                    # Only update if value is different or doesn't exist
                    if key not in data_product or data_product[key] != value:
                        data_product[key] = value
                state["data_product"] = data_product
            
            # Update policy pack state (avoid duplicates)
            if validated_output.parsed_policies:
                policy_pack = state.get("policy_pack", {})
                for key, value in validated_output.parsed_policies.items():
                    # Only update if value is different or doesn't exist
                    if key not in policy_pack or policy_pack[key] != value:
                        policy_pack[key] = value
                state["policy_pack"] = policy_pack
            
            # Check if all required fields are complete
            ask_order = self.get_config_list("ask_order", ["access_control", "data_masking", "quality_gates", "retention_policy", "evaluation_points"])
            policy_pack = state.get("policy_pack", {})
            
            # Check if all fields are present
            all_fields_complete = all(
                field in policy_pack and policy_pack[field] 
                for field in ask_order
            )
            
            if all_fields_complete:
                completion_message = self.get_config("completion_message", "Policy configuration captured.")
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
                "missing_fields": validated_output.missing_fields,
                "parsed_policies": validated_output.parsed_policies
            }
            
        except Exception as e:
            # Preserve the current state even when there's an error
            policy_pack = state.get("policy_pack", {})
            
            # Create a helpful error message that maintains context
            error_message = f"I encountered an issue processing your message: {str(e)}. "
            
            # Check what we have so far and provide context
            if policy_pack:
                error_message += "Here's what I have so far:\n"
                for key, value in policy_pack.items():
                    error_message += f"- {key}: {value}\n"
                error_message += "\nPlease continue providing the missing information."
            else:
                error_message += "Let me help you start defining your data product policies. What access control rules do you need?"
            
            return {
                "reply": error_message,
                "confidence": 0.0,
                "next_action": "retry",
                "metadata": {"error": str(e), "state_preserved": True},
                "extracted_data": {},
                "missing_fields": [],
                "parsed_policies": {}
            }
