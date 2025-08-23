"""
Structured Policy Agent using OpenAI structured output and Pydantic models.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .base_structured import BaseStructuredAgent, Message

class PolicyInput(BaseModel):
    """Input model for policy agent."""
    message: str = Field(description="The user's message")
    role: str = Field(description="The role of the message sender")
    state: Dict[str, Any] = Field(description="Current conversation state")
    policy_pack: Dict[str, Any] = Field(default_factory=dict, description="Current policy pack")

class PolicyOutput(BaseModel):
    """Output model for policy agent."""
    reply: str = Field(description="The response message to send to the user")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence level of the response")
    next_action: Optional[str] = Field(default=None, description="Suggested next action for the user")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    command_type: Optional[str] = Field(default=None, description="Type of command detected (allow, deny, mask, gate, retention, policies_done)")
    extracted_data: Dict[str, Any] = Field(default_factory=dict, description="Extracted data from the message")
    policy_updates: Dict[str, Any] = Field(default_factory=dict, description="Policy updates to apply")

class PolicyAgentStructured(BaseStructuredAgent):
    name = "policy"
    
    def get_input_model(self) -> type[PolicyInput]:
        return PolicyInput
    
    def get_output_model(self) -> type[PolicyOutput]:
        return PolicyOutput
    
    def get_system_prompt(self) -> str:
        commands = self.get_config_dict("commands", {})
        help_message = self.get_config("help_message", "Add policy with `allow:role1,role2`, `deny:role3`, `mask:column=email,role=*`, `gate:type=not_null,column=customer_id`, `retention:mode=delete,duration=365d` or `policies:done`.")
        
        prompt = f"""You are a data product policy agent. Your job is to help users define access controls, data masking, quality gates, and retention policies.

Available commands:
1. allow: Define allowed roles (e.g., "allow:role:marketing-analyst,role:crm-engineer")
2. deny: Define denied roles (e.g., "deny:role:intern")
3. mask: Define column masking (e.g., "mask:column=email,role=*")
4. gate: Define quality gates (e.g., "gate:type=not_null,column=customer_id")
5. retention: Define retention policies (e.g., "retention:mode=delete,duration=365d")
6. policies:done: Complete policy definition

Command configurations:
{chr(10).join([f"- {cmd}: {config.get('success_template', 'No template available')}" for cmd, config in commands.items()])}

Help message: {help_message}

Your task:
1. Detect the command type from the user's message
2. Extract relevant data from the message
3. Provide appropriate response based on the command
4. Suggest next actions

Respond with a JSON object containing:
- reply: Your response message
- confidence: Your confidence level (0.0 to 1.0)
- next_action: Suggested next action (e.g., "add_mask", "add_gate", "complete")
- metadata: Any additional information
- command_type: Type of command detected
- extracted_data: Any data you extracted from the message
- policy_updates: Any policy updates to apply

Be helpful and guide the user through the policy definition process."""
        
        return prompt
    
    def extract_structured_input(self, message: Message, state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured input from message and state."""
        return {
            "message": message.content,
            "role": message.role,
            "state": state,
            "policy_pack": state.get("policy_pack", {})
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
                    {"role": "user", "content": f"User message: {validated_input.message}\nCurrent policy pack: {validated_input.policy_pack}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            # Parse and validate response
            response_content = response.choices[0].message.content
            output_model = self.get_output_model()
            validated_output = output_model.model_validate_json(response_content)
            
            # Apply policy updates
            if validated_output.policy_updates:
                self._apply_policy_updates(state, validated_output)
            
            # Update state with extracted data
            if validated_output.extracted_data:
                policy_pack = state.setdefault("policy_pack", {})
                policy_pack.update(validated_output.extracted_data)
            
            # Convert to dict format expected by the system
            return {
                "reply": validated_output.reply,
                "confidence": validated_output.confidence,
                "next_action": validated_output.next_action,
                "metadata": validated_output.metadata
            }
            
        except Exception as e:
            print(f"Error in structured policy agent: {e}")
            # Fallback to simple response
            return {
                "reply": f"I encountered an error processing your request: {str(e)}",
                "confidence": 0.0,
                "next_action": "help",
                "metadata": {"error": str(e)}
            }
    
    def _apply_policy_updates(self, state: Dict[str, Any], output: PolicyOutput):
        """Apply policy updates to the state."""
        command_type = output.command_type
        policy_pack = state.setdefault("policy_pack", {})
        
        if command_type == "allow":
            # Handle allow command
            if output.extracted_data and "roles" in output.extracted_data:
                access = policy_pack.setdefault("access", {})
                allow_roles = access.setdefault("allow_roles", [])
                allow_roles.extend(output.extracted_data["roles"])
        
        elif command_type == "deny":
            # Handle deny command
            if output.extracted_data and "roles" in output.extracted_data:
                access = policy_pack.setdefault("access", {})
                deny_roles = access.setdefault("deny_roles", [])
                deny_roles.extend(output.extracted_data["roles"])
        
        elif command_type == "mask":
            # Handle mask command
            if output.extracted_data:
                access = policy_pack.setdefault("access", {})
                column_masks = access.setdefault("column_masks", [])
                
                mask_config = output.extracted_data
                new_mask = {
                    "column": mask_config.get("column", ""),
                    "masking_expression": mask_config.get("masking_expression", ""),
                    "applies_to_roles": mask_config.get("applies_to_roles", ["*"])
                }
                column_masks.append(new_mask)
        
        elif command_type == "gate":
            # Handle gate command
            if output.extracted_data:
                quality_gates = policy_pack.setdefault("quality_gates", [])
                gate_config = output.extracted_data
                
                new_gate = {
                    "name": gate_config.get("name", ""),
                    "type": gate_config.get("type", "not_null")
                }
                
                if "column" in gate_config:
                    new_gate["column"] = gate_config["column"]
                if "pattern" in gate_config:
                    new_gate["pattern"] = gate_config["pattern"]
                if "max_delay" in gate_config:
                    new_gate["max_delay"] = gate_config["max_delay"]
                
                quality_gates.append(new_gate)
        
        elif command_type == "retention":
            # Handle retention command
            if output.extracted_data:
                policy_pack["retention"] = output.extracted_data
