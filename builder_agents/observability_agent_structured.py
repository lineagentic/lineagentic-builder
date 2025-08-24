"""
Structured Observability Agent using OpenAI structured output and Pydantic models.
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from .base_structured import BaseStructuredAgent, Message

class ObservabilityInput(BaseModel):
    """Input model for observability agent."""
    conversation_context: str = Field(description="Full conversation context including history")
    current_state: Dict[str, Any] = Field(description="Current conversation state")

class ObservabilityOutput(BaseModel):
    """Output model for observability agent."""
    reply: str = Field(description="The response message to send to the user")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence level of the response")
    next_action: Optional[str] = Field(default=None, description="Suggested next action for the user")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    extracted_data: Dict[str, Any] = Field(default_factory=dict, description="Extracted data from the message")
    missing_fields: List[str] = Field(default_factory=list, description="List of missing required fields")

class ObservabilityAgentStructured(BaseStructuredAgent):
    name = "observability"
    
    def get_input_model(self) -> type[ObservabilityInput]:
        return ObservabilityInput
    
    def get_output_model(self) -> type[ObservabilityOutput]:
        return ObservabilityOutput
    
    def get_system_prompt(self) -> str:
        ask_order = self.get_config_list("ask_order", ["metrics", "alerts", "dashboards", "latency_threshold", "availability_target"])
        prompts = self.get_config_dict("prompts", {})
        completion_message = self.get_config("completion_message", "Observability configuration captured.")
        
        prompt = f"""You are an observability agent. Your job is to help users configure monitoring and observability settings for their data product.

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
- If "observability" exists in data_product, check if it contains:
  * "metrics" - metrics are configured
  * "alerts" - alerts are configured
  * "dashboards" - dashboards are configured
  * "latency_threshold" - latency threshold is set
  * "availability_target" - availability target is set
- If ALL of these fields exist in observability, observability is COMPLETE
- If user says "yes" to monitoring and observability is complete, acknowledge completion
- If user asks "what is next" and observability is complete, provide completion message
- NEVER ask for observability fields that are already configured

NATURAL LANGUAGE UNDERSTANDING:
- Users can say things naturally, not just with explicit keywords
- "metrics" = metrics
- "monitoring" = metrics
- "alerts" = alerts
- "notifications" = alerts
- "dashboards" = dashboards
- "reports" = dashboards
- "latency" = latency_threshold
- "response time" = latency_threshold
- "availability" = availability_target
- "uptime" = availability_target
- "yes" to monitoring question = acknowledge if monitoring is already configured

METRIC EXTRACTION:
- "freshness" = metrics: ["freshness"]
- "completeness" = metrics: ["completeness"]
- "accuracy" = metrics: ["accuracy"]
- "volume" = metrics: ["volume"]
- "quality score" = metrics: ["quality_score"]
- "processing time" = metrics: ["processing_time"]
- "latency" = metrics: ["latency"]
- "throughput" = metrics: ["throughput"]
- "error rate" = metrics: ["error_rate"]
- "success rate" = metrics: ["success_rate"]

MULTIPLE METRICS:
- If user mentions multiple metrics, extract all of them
- "freshness, completeness, accuracy" = metrics: ["freshness", "completeness", "accuracy"]
- "all metrics" = metrics: ["freshness", "completeness", "accuracy", "volume", "quality_score", "processing_time"]

OBSERVABILITY COMPLETION DETECTION:
- If user says "yes" to monitoring and observability is already configured, acknowledge completion
- If user provides metrics and they're already captured, acknowledge and move to next step
- If user asks "what is next" and observability is complete, provide completion message

Your task:
1. First, analyze the conversation context to understand current progress
2. Extract any observability configuration information from the user's message
3. Identify what observability fields are still missing (only ask for uncaptured fields)
4. Provide a helpful response guiding the user to the next missing field
5. If all fields are complete, provide the completion message

IMPORTANT RULES:
- If user says "freshness", extract metrics: ["freshness"]
- If user says "completeness", extract metrics: ["completeness"]
- If user says "accuracy", extract metrics: ["accuracy"]
- If user mentions multiple metrics, extract all of them
- NEVER ask for the same field twice if it's already been provided
- CHECK THE CURRENT STATE FIRST - if a field is already set, don't ask for it again

IMPORTANT: Always provide clear examples in your responses to help users understand what you're asking for.

Respond with a JSON object containing:
- reply: Your response message (include examples when asking for information)
- confidence: Your confidence level (0.0 to 1.0)
- next_action: Suggested next action (e.g., "provide_metrics", "provide_alerts", "complete")
- metadata: Any additional information
- extracted_data: Any observability configuration data you extracted from the message
- missing_fields: List of observability fields that are still missing

Be helpful and guide the user through the observability configuration process step by step with clear examples, but never repeat questions for information already provided."""
        
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
            
            # Update state with extracted data (avoid duplicates)
            if validated_output.extracted_data:
                data_product = state.setdefault("data_product", {})
                observability_config = data_product.setdefault("observability", {})
                for key, value in validated_output.extracted_data.items():
                    # Only update if value is different or doesn't exist
                    if key not in observability_config or observability_config[key] != value:
                        observability_config[key] = value
            
            # Convert to dict format expected by the system
            return {
                "reply": validated_output.reply,
                "confidence": validated_output.confidence,
                "next_action": validated_output.next_action,
                "metadata": validated_output.metadata
            }
            
        except Exception as e:
            print(f"Error in structured observability agent: {e}")
            # Preserve existing state and provide context-aware error message
            data_product = state.get("data_product", {})
            observability_config = data_product.get("observability", {})
            
            if observability_config:
                return {
                    "reply": f"I encountered an error processing your observability request, but I can see you have observability configuration already set up. Could you please clarify what specific aspect of monitoring or observability you'd like to address?",
                    "confidence": 0.0,
                    "next_action": "help",
                    "metadata": {"error": str(e), "existing_config": True}
                }
            else:
                return {
                    "reply": f"I encountered an error processing your observability request: {str(e)}. Let me help you set up the monitoring and observability configuration for your data product.",
                    "confidence": 0.0,
                    "next_action": "help",
                    "metadata": {"error": str(e)}
                }
