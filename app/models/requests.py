"""Request models for OpenAI-compatible API."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class ChatMessage(BaseModel):
    """Individual chat message."""
    
    role: str = Field(..., description="Role of the message sender")
    content: str = Field(..., description="Content of the message")
    name: Optional[str] = Field(None, description="Name of the message sender")
    
    @validator("role")
    def validate_role(cls, v: str) -> str:
        """Validate message role.
        
        Args:
            v: Role value
            
        Returns:
            Validated role
            
        Raises:
            ValueError: If role is invalid
        """
        allowed_roles = {"system", "user", "assistant", "function"}
        if v not in allowed_roles:
            raise ValueError(f"Role must be one of {allowed_roles}")
        return v


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request."""
    
    model: str = Field(..., description="Model to use for completion")
    messages: List[ChatMessage] = Field(..., description="List of chat messages")
    temperature: Optional[float] = Field(
        1.0, 
        ge=0.0, 
        le=2.0, 
        description="Sampling temperature"
    )
    max_tokens: Optional[int] = Field(
        None, 
        gt=0, 
        description="Maximum tokens to generate"
    )
    top_p: Optional[float] = Field(
        1.0, 
        ge=0.0, 
        le=1.0, 
        description="Nucleus sampling parameter"
    )
    frequency_penalty: Optional[float] = Field(
        0.0, 
        ge=-2.0, 
        le=2.0, 
        description="Frequency penalty"
    )
    presence_penalty: Optional[float] = Field(
        0.0, 
        ge=-2.0, 
        le=2.0, 
        description="Presence penalty"
    )
    stream: bool = Field(False, description="Whether to stream responses")
    user: Optional[str] = Field(None, description="User identifier")
    
    @validator("messages")
    def validate_messages_not_empty(cls, v: List[ChatMessage]) -> List[ChatMessage]:
        """Validate messages list is not empty.
        
        Args:
            v: Messages list
            
        Returns:
            Validated messages list
            
        Raises:
            ValueError: If messages list is empty
        """
        if not v:
            raise ValueError("Messages list cannot be empty")
        return v