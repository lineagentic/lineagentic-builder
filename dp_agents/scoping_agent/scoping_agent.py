"""
Structured Scoping Agent using OpenAI structured output and Pydantic models.
"""
from typing import Dict, Any, List, Optional
import os
import logging
import yaml
from pathlib import Path
from pydantic import BaseModel, Field
from openai import OpenAI

logger = logging.getLogger(__name__)

class Message:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

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

class ScopingAgentStructured:
    name = "scoping"
    
    def __init__(self, openai_client: Optional[OpenAI] = None, config_path: Optional[str] = None):
        """
        Initialize the scoping agent with OpenAI client and YAML configuration.
        
        Args:
            openai_client: OpenAI client instance (required)
            config_path: Path to YAML configuration file (optional)
        """
        # Initialize OpenAI client
        if openai_client is None:
            # Try to get from environment as fallback
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.error("OpenAI client is required for scoping agent")
                raise ValueError("OpenAI client is required for agent initialization")
            self.client = OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized from environment for scoping agent")
        else:
            self.client = openai_client
            logger.info("OpenAI client provided for scoping agent")
        
        # Load YAML configuration
        self.config = self._load_config(config_path)
        logger.info("Scoping agent configuration loaded successfully")
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load YAML configuration file."""
        if config_path is None:
            # Default to scoping_config.yaml in the same directory
            config_path = Path(__file__).parent / "scoping_config.yaml"
        
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
                logger.info(f"Configuration loaded from {config_path}")
                return config
        except FileNotFoundError:
            error_msg = f"Configuration file not found at {config_path}. YAML configuration is required."
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        except yaml.YAMLError as e:
            error_msg = f"Error parsing YAML configuration: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def get_input_model(self) -> type[ScopingInput]:
        return ScopingInput
    
    def get_output_model(self) -> type[ScopingOutput]:
        return ScopingOutput
    
    def get_system_prompt(self) -> str:
        """Get the system prompt from YAML configuration with dynamic field references."""
        system_prompt = self.config.get("system_prompt", "")
        
        # Replace placeholder with actual required fields
        required_fields = self.get_required_fields()
        required_fields_list = "\n".join([f"  {i+1}) {field}" for i, field in enumerate(required_fields)])
        
        # Replace placeholder with field descriptions
        field_descriptions = self.config.get("field_descriptions", {})
        field_descriptions_list = self._build_field_descriptions_list(field_descriptions)
        
        # Use string replacement instead of format() to avoid conflicts with JSON braces
        system_prompt = system_prompt.replace("{required_fields_list}", required_fields_list)
        system_prompt = system_prompt.replace("{field_descriptions_list}", field_descriptions_list)
        
        return system_prompt
    
    def _build_field_descriptions_list(self, field_descriptions: Dict[str, Any]) -> str:
        """Build a formatted list of field descriptions for the system prompt."""
        if not field_descriptions:
            return ""
        
        descriptions = []
        for field_name, field_info in field_descriptions.items():
            if isinstance(field_info, dict):
                description = field_info.get("description", "")
                example = field_info.get("example", "")
                normalize = field_info.get("Normalize", "")
                required = field_info.get("Required", True)
                
                field_text = f"  {field_name}:"
                if description:
                    field_text += f" {description}"
                if example:
                    field_text += f" (e.g., {example})"
                if normalize:
                    field_text += f" - Normalize: {normalize}"
                if not required:
                    field_text += " (optional)"
                
                descriptions.append(field_text)
            else:
                # Fallback for simple string descriptions
                descriptions.append(f"  {field_name}: {field_info}")
        
        return "\n".join(descriptions)
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value from YAML config."""
        return self.config.get(key, default)
    
    def get_config_list(self, key: str, default: List[Any] = None) -> List[Any]:
        """Get a configuration list value from YAML config."""
        return self.config.get(key, default or [])
    
    def get_required_fields(self) -> List[str]:
        """Get the list of required fields from YAML config."""
        return self.config.get("required_fields", ["name", "domain", "owner", "purpose", "upstreams"])
    
    def enhance_reply_with_example(self, reply: str, field_name: str = None) -> str:
        """Enhance a reply with relevant examples."""
        # Examples are embedded in the instruction files, so just return the reply
        return reply
    
    def _build_conversation_context(self, state: Dict[str, Any]) -> str:
        """Build conversation context including history and current state."""
        context_parts = []
        
        # Add current data product state
        data_product = state.get("data_product", {})
        if data_product:
            context_parts.append("Current Data Product State:")
            for key, value in data_product.items():
                if value:  # Only include non-empty values
                    context_parts.append(f"- {key}: {value}")
        
        # Add recent conversation history (last 5 exchanges)
        history = state.get("history", [])
        if history:
            context_parts.append("\nRecent Conversation History:")
            # Get last 10 messages (5 exchanges)
            recent_history = history[-10:] if len(history) > 10 else history
            for msg in recent_history:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if content:
                    context_parts.append(f"- {role}: {content[:100]}...")
        
        return "\n".join(context_parts) if context_parts else "No previous context available."
    
    async def handle_async(self, state: Dict[str, Any], message: Message) -> Dict[str, Any]:
        """Handle message using OpenAI structured output."""
        logger.info(f"Scoping agent processing message: {message.content[:50]}...")
        
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
            
            # Call OpenAI with structured output
            logger.info("Scoping agent calling OpenAI API...")
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Conversation Context:\n{conversation_context}\n\nCurrent Message: {message.content}"}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1
                )
            )
            
            # Parse the response
            response_content = response.choices[0].message.content
            logger.debug(f"Scoping agent OpenAI response: {response_content[:200]}...")
            validated_output = ScopingOutput.model_validate_json(response_content)
            logger.info(f"Scoping agent response validated successfully. Confidence: {validated_output.confidence}")
            
            # Update conversation state (avoid duplicates)
            if validated_output.extracted_data:
                data_product = state.get("data_product", {})
                for key, value in validated_output.extracted_data.items():
                    # Only update if value is different or doesn't exist
                    if key not in data_product or data_product[key] != value:
                        data_product[key] = value
                state["data_product"] = data_product
            
            # Check if all required fields are complete (using YAML config)
            required_fields = self.get_required_fields()
            data_product = state.get("data_product", {})
            
            # Check if all fields are present
            all_fields_complete = all(
                field in data_product and data_product[field] 
                for field in required_fields
            )
            
            if all_fields_complete:
                completion_message = self.get_config("completion_message", "Scope captured.")
                validated_output.reply = completion_message
                validated_output.next_action = "complete"
            
            # Enhance reply with examples
            reply = self.enhance_reply_with_example(validated_output.reply, validated_output.next_action)
            
            logger.info("Scoping agent processing completed successfully")
            return {
                "reply": reply,
                "confidence": validated_output.confidence,
                "next_action": validated_output.next_action,
                "metadata": validated_output.metadata,
                "extracted_data": validated_output.extracted_data,
                "missing_fields": validated_output.missing_fields
            }
            
        except Exception as e:
            logger.error(f"Scoping agent error: {e}")
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
