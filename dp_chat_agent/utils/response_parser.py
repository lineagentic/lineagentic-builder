"""
Response parser module for extracting structured data from agent responses.
"""
import os
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from openai import OpenAI


class AgentResponseParser(BaseModel):
    """Pydantic model for parsing structured agent responses."""
    reply: Optional[str] = Field(default=None, description="The clean response message without structured data")
    clean_reply_message: Optional[str] = Field(default=None, description="Alternative field name for clean reply")
    extracted_data: Dict[str, Any] = Field(default_factory=dict, description="Any data extracted from the user input")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence level of the response")
    next_action: Optional[str] = Field(default=None, description="Suggested next action")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    missing_fields: List[str] = Field(default_factory=list, description="List of missing required fields")
    
    def get_reply(self) -> str:
        """Get the reply from either field"""
        return self.reply or self.clean_reply_message or ""


class ResponseParser:
    """Class for parsing agent responses using OpenAI structured output."""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def parse_agent_response(self, final_output: str) -> AgentResponseParser:
        """
        Parse the agent response using structured output.
        
        Args:
            final_output: The raw agent response string
            
        Returns:
            AgentResponseParser: Parsed structured data
        """
        parse_prompt = f"""
        Parse the following agent response and extract the structured information.
        
        Agent Response:
        {str(final_output)}
        
        Return a JSON object with these exact fields:
        - "reply": The clean response message (remove any structured data sections)
        - "extracted_data": Object with any extracted data (like {{"name": "value"}})
        - "confidence": Number between 0 and 1
        - "next_action": String describing next action
        - "metadata": Object with additional metadata
        - "missing_fields": Array of missing field names
        
        Look for patterns like:
        - "I have noted that the name of your data product is 'X'" -> extract name
        - "Confidence: 0.95" -> extract confidence
        - "Missing required fields: - field1 - field2" -> extract missing fields
        - "Domain", "Owner", "Purpose" mentioned -> these are likely missing fields
        """
        
        response = self.openai_client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a parser that extracts structured data from agent responses. Return only valid JSON."},
                {"role": "user", "content": parse_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        # Parse the structured response
        parsed_data = AgentResponseParser.model_validate_json(response.choices[0].message.content)
        return parsed_data
