"""
Base agent framework with OpenAI structured output support.
Uses Pydantic models for controlled inputs and outputs.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Type, Union
import copy
import sys
import os
import logging
from abc import ABC, abstractmethod

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel, Field
from openai import OpenAI
from config import get_agent_config

# Configure logging
logger = logging.getLogger(__name__)

class Message:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

class AgentResponse(BaseModel):
    """Base model for agent responses."""
    reply: str = Field(description="The response message to send to the user")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence level of the response")
    next_action: Optional[str] = Field(default=None, description="Suggested next action for the user")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class BaseStructuredAgent(ABC):
    """Base class for agents using OpenAI structured output."""
    
    name: str = "base"
    
    def __init__(self, config_dir: Optional[str] = None, openai_client: Optional[OpenAI] = None):
        """
        Initialize the agent with configuration and OpenAI client.
        
        Args:
            config_dir: Optional path to configuration directory
            openai_client: OpenAI client instance (required)
        """
        self.config_dir = config_dir
        self._config = None
        self._load_config_sync()
        
        # Initialize OpenAI client
        if openai_client is None:
            # Try to get from environment as fallback
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.error(f"OpenAI client is required for {self.name} agent")
                raise ValueError("OpenAI client is required for agent initialization")
            self.client = OpenAI(api_key=api_key)
            logger.info(f"OpenAI client initialized from environment for {self.name} agent")
        else:
            self.client = openai_client
            logger.info(f"OpenAI client provided for {self.name} agent")
    
    async def _load_config(self):
        """Load configuration for this agent."""
        try:
            # Extract agent name from class name (e.g., ScopingAgent -> scoping)
            agent_name = self.name
            self._config = await get_agent_config(agent_name, self.config_dir)
            logger.info(f"Configuration loaded for {self.name} agent: {len(self._config)} keys")
        except Exception as e:
            logger.warning(f"Could not load config for {self.name}: {e}")
            self._config = {}
    
    def _load_config_sync(self):
        """Synchronous version for backward compatibility."""
        import asyncio
        try:
            # Try to get the current event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in an async context, schedule the async call
                asyncio.create_task(self._load_config())
            except RuntimeError:
                # No running loop, create one
                asyncio.run(self._load_config())
        except Exception as e:
            logger.warning(f"Could not load config for {self.name}: {e}")
            self._config = {}
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_config_list(self, key: str, default: List[Any] = None) -> List[Any]:
        """
        Get a configuration list value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration list or default
        """
        value = self.get_config(key, default or [])
        return value if isinstance(value, list) else default or []
    
    def get_config_dict(self, key: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get a configuration dictionary value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration dict or default
        """
        value = self.get_config(key, default or {})
        return value if isinstance(value, dict) else default or {}
    
    def format_template(self, template: str, **kwargs) -> str:
        """
        Format a template string with provided values.
        
        Args:
            template: Template string with placeholders
            kwargs: Values to substitute
            
        Returns:
            Formatted string
        """
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing template key {e} in template: {template}")
            return template
    
    def get_example_for_field(self, field_name: str) -> str:
        """
        Get an example for a specific field from the config.
        
        Args:
            field_name: Name of the field to get example for
            
        Returns:
            Example string for the field
        """
        prompts = self.get_config_dict("prompts", {})
        if field_name in prompts:
            prompt = prompts[field_name]
            # Extract example from prompt (after "Example:")
            if "Example:" in prompt:
                example_part = prompt.split("Example:")[1].strip()
                return example_part
        return ""
    
    def get_next_field_example(self, current_field: str) -> str:
        """
        Get the next field in ask_order and its example.
        
        Args:
            current_field: Current field being processed
            
        Returns:
            Example for the next field
        """
        ask_order = self.get_config_list("ask_order", [])
        try:
            current_index = ask_order.index(current_field)
            if current_index + 1 < len(ask_order):
                next_field = ask_order[current_index + 1]
                return self.get_example_for_field(next_field)
        except ValueError:
            pass
        return ""
    
    def enhance_reply_with_example(self, reply: str, field_name: str = None) -> str:
        """
        Enhance a reply with relevant examples.
        
        Args:
            reply: Original reply message
            field_name: Current field being processed
            
        Returns:
            Enhanced reply with examples
        """
        if field_name:
            example = self.get_example_for_field(field_name)
            if example:
                return f"{reply}\n\nExample: {example}"
        
        return reply
    
    @abstractmethod
    def get_input_model(self) -> Type[BaseModel]:
        """Return the Pydantic model for input validation."""
        pass
    
    @abstractmethod
    def get_output_model(self) -> Type[BaseModel]:
        """Return the Pydantic model for output validation."""
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass
    
    def extract_structured_input(self, message: Message, state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured input from message and state."""
        # Default implementation - can be overridden by subclasses
        return {
            "message": message.content,
            "role": message.role,
            "state": state
        }
    
    def handle(self, state: Dict[str, Any], message: Message) -> Dict[str, Any]:
        """Handle message using OpenAI structured output (synchronous)."""
        import asyncio
        try:
            # Try to run async version if in async context
            loop = asyncio.get_running_loop()
            # If we're in an async context, schedule the async call
            future = asyncio.create_task(self.handle_async(state, message))
            # Wait for the result
            return asyncio.run_coroutine_threadsafe(future, loop).result()
        except RuntimeError:
            # No running loop, run async version in new loop
            return asyncio.run(self.handle_async(state, message))
    
    async def handle_async(self, state: Dict[str, Any], message: Message) -> Dict[str, Any]:
        """Handle message using OpenAI structured output (asynchronous)."""
        logger.info(f"{self.name} agent processing message: {message.content[:50]}...")
        
        try:
            # Extract structured input
            input_data = self.extract_structured_input(message, state)
            logger.debug(f"{self.name} agent input data: {input_data}")
            
            # Validate input using Pydantic model
            input_model = self.get_input_model()
            validated_input = input_model(**input_data)
            logger.debug(f"{self.name} agent input validated successfully")
            
            # Get system prompt
            system_prompt = self.get_system_prompt()
            logger.debug(f"{self.name} agent system prompt length: {len(system_prompt)}")
            
            # Build conversation context including history
            conversation_context = self._build_conversation_context(state)
            
            # Call OpenAI with structured output
            logger.info(f"{self.name} agent calling OpenAI API...")
            # Use run_in_executor to make the sync call async
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model="gpt-4-turbo-preview",  # or use config
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Conversation Context:\n{conversation_context}\n\nCurrent Message: {validated_input}"}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1
                )
            )
            
            # Parse and validate response
            response_content = response.choices[0].message.content
            logger.debug(f"{self.name} agent OpenAI response: {response_content[:200]}...")
            
            output_model = self.get_output_model()
            validated_output = output_model.model_validate_json(response_content)
            logger.info(f"{self.name} agent response validated successfully. Confidence: {validated_output.confidence}")
            
            # Convert to dict format expected by the system
            result = {
                "reply": validated_output.reply,
                "confidence": validated_output.confidence,
                "next_action": validated_output.next_action,
                "metadata": validated_output.metadata
            }
            
            logger.info(f"{self.name} agent processing completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"{self.name} agent error: {e}")
            # Fallback to simple response
            return {
                "reply": f"I encountered an error processing your request: {str(e)}",
                "confidence": 0.0,
                "next_action": "help",
                "metadata": {"error": str(e)}
            }
    
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
        
        # Add current policy pack state
        policy_pack = state.get("policy_pack", {})
        if policy_pack:
            context_parts.append("\nCurrent Policy Pack State:")
            for key, value in policy_pack.items():
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

def deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries."""
    out = copy.deepcopy(a)
    for k,v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out
