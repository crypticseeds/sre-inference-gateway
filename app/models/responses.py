"""Response models for OpenAI-compatible API."""

import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatCompletionChoice(BaseModel):
    """Individual choice in chat completion response."""
    
    index: int = Field(..., description="Choice index")
    message: Dict[str, Any] = Field(..., description="Response message")
    finish_reason: Optional[str] = Field(None, description="Reason for completion")


class ChatCompletionUsage(BaseModel):
    """Token usage information."""
    
    prompt_tokens: int = Field(..., description="Tokens in the prompt")
    completion_tokens: int = Field(..., description="Tokens in the completion")
    total_tokens: int = Field(..., description="Total tokens used")


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response."""
    
    id: str = Field(..., description="Unique completion ID")
    object: str = Field("chat.completion", description="Object type")
    created: int = Field(default_factory=lambda: int(time.time()), description="Creation timestamp")
    model: str = Field(..., description="Model used for completion")
    choices: List[ChatCompletionChoice] = Field(..., description="List of completion choices")
    usage: ChatCompletionUsage = Field(..., description="Token usage information")


class ErrorDetail(BaseModel):
    """Error detail information."""
    
    message: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")
    param: Optional[str] = Field(None, description="Parameter that caused error")
    code: Optional[str] = Field(None, description="Error code")


class ErrorResponse(BaseModel):
    """Error response format."""
    
    error: ErrorDetail = Field(..., description="Error details")