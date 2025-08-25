"""
Structured Routing Agent using OpenAI structured output and Pydantic models.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .base import BaseStructuredAgent, Message

class RoutingInput(BaseModel):
    """Input model for routing agent."""
    message: str = Field(description="The user's message")
    conversation_context: str = Field(description="Current conversation context")
    available_agents: List[str] = Field(description="List of available agents")
    current_state: Dict[str, Any] = Field(description="Current conversation state")

class RoutingOutput(BaseModel):
    """Output model for routing agent."""
    selected_agent: str = Field(description="The agent to route the message to")
    reasoning: str = Field(description="Explanation for why this agent was chosen")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence level of the routing decision")
    user_intent: str = Field(description="What the user is trying to accomplish")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class RoutingAgentStructured(BaseStructuredAgent):
    name = "routing"
    
    def get_input_model(self) -> type[RoutingInput]:
        return RoutingInput
    
    def get_output_model(self) -> type[RoutingOutput]:
        return RoutingOutput
    
    def get_system_prompt(self) -> str:
        from .routing_agent_instructions import ROUTING_AGENT_SYSTEM_PROMPT
        return ROUTING_AGENT_SYSTEM_PROMPT
    
    def extract_structured_input(self, message: Message, state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured input from message and state."""
        # Get available agents from the state or use default list
        available_agents = state.get("available_agents", ["scoping", "data_contract", "policy", "provisioning", "docs", "catalog", "observability"])
        
        return {
            "message": message.content,
            "role": message.role,
            "state": state,
            "available_agents": available_agents
        }
    
    async def handle_async(self, state: Dict[str, Any], message: Message) -> Dict[str, Any]:
        """Handle message using OpenAI structured output."""
        try:
            # Build conversation context
            conversation_context = self._build_conversation_context(state)
            
            # Get available agents (this could be passed from the server)
            available_agents = ["scoping", "data_contract", "policy", "provisioning", "docs", "catalog", "observability"]
            
            # Create input for the agent
            input_data = RoutingInput(
                message=message.content,
                conversation_context=conversation_context,
                available_agents=available_agents,
                current_state=state
            )
            
            # Get system prompt
            system_prompt = self.get_system_prompt()
            
            # Call OpenAI with structured output using the base class method
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Conversation Context:\n{conversation_context}\n\nAvailable Agents: {available_agents}\n\nCurrent Message: {message.content}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            # Parse the response
            response_content = response.choices[0].message.content
            validated_output = RoutingOutput.model_validate_json(response_content)
            
            return {
                "selected_agent": validated_output.selected_agent,
                "reasoning": validated_output.reasoning,
                "confidence": validated_output.confidence,
                "user_intent": validated_output.user_intent,
                "metadata": validated_output.metadata
            }
            
        except Exception as e:
            # Return a safe default routing decision
            return {
                "selected_agent": "scoping",
                "reasoning": f"Default routing due to error: {str(e)}",
                "confidence": 0.0,
                "user_intent": "Unknown - routing error occurred",
                "metadata": {"error": str(e)}
            }
