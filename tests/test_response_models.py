"""Tests for response models with enhanced token tracking."""

import json
import time

import pytest
from pydantic import ValidationError

from app.models.responses import (
    ChatCompletionChoice,
    ChatCompletionUsage,
    ChatCompletionResponse,
    ErrorDetail,
    ErrorResponse,
)


class TestChatCompletionChoice:
    """Test ChatCompletionChoice model."""

    def test_valid_choice(self):
        """Test valid choice creation."""
        choice = ChatCompletionChoice(
            index=0,
            message={"role": "assistant", "content": "Hello!"},
            finish_reason="stop"
        )
        
        assert choice.index == 0
        assert choice.message["role"] == "assistant"
        assert choice.message["content"] == "Hello!"
        assert choice.finish_reason == "stop"

    def test_choice_without_finish_reason(self):
        """Test choice creation without finish_reason."""
        choice = ChatCompletionChoice(
            index=1,
            message={"role": "assistant", "content": "Test"}
        )
        
        assert choice.index == 1
        assert choice.finish_reason is None

    def test_choice_serialization(self):
        """Test choice serialization to dict."""
        choice = ChatCompletionChoice(
            index=0,
            message={"role": "assistant", "content": "Test"},
            finish_reason="length"
        )
        
        data = choice.model_dump()
        assert data["index"] == 0
        assert data["message"]["content"] == "Test"
        assert data["finish_reason"] == "length"


class TestChatCompletionUsage:
    """Test ChatCompletionUsage model with enhanced token tracking."""

    def test_basic_usage(self):
        """Test basic token usage without details."""
        usage = ChatCompletionUsage(
            prompt_tokens=25,
            completion_tokens=50,
            total_tokens=75
        )
        
        assert usage.prompt_tokens == 25
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 75
        assert usage.prompt_tokens_details is None
        assert usage.completion_tokens_details is None

    def test_enhanced_usage_with_details(self):
        """Test enhanced token usage with detailed breakdown."""
        usage = ChatCompletionUsage(
            prompt_tokens=100,
            completion_tokens=80,
            total_tokens=180,
            prompt_tokens_details={
                "cached_tokens": 20,
                "audio_tokens": 0
            },
            completion_tokens_details={
                "reasoning_tokens": 30,
                "audio_tokens": 0,
                "accepted_prediction_tokens": 5,
                "rejected_prediction_tokens": 2
            }
        )
        
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 80
        assert usage.total_tokens == 180
        
        # Test prompt token details
        assert usage.prompt_tokens_details["cached_tokens"] == 20
        assert usage.prompt_tokens_details["audio_tokens"] == 0
        
        # Test completion token details
        assert usage.completion_tokens_details["reasoning_tokens"] == 30
        assert usage.completion_tokens_details["audio_tokens"] == 0
        assert usage.completion_tokens_details["accepted_prediction_tokens"] == 5
        assert usage.completion_tokens_details["rejected_prediction_tokens"] == 2

    def test_partial_token_details(self):
        """Test usage with only some token details."""
        usage = ChatCompletionUsage(
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
            prompt_tokens_details={"cached_tokens": 15}
            # completion_tokens_details intentionally omitted
        )
        
        assert usage.prompt_tokens_details["cached_tokens"] == 15
        assert usage.completion_tokens_details is None

    def test_usage_serialization(self):
        """Test usage serialization with enhanced details."""
        usage = ChatCompletionUsage(
            prompt_tokens=40,
            completion_tokens=60,
            total_tokens=100,
            prompt_tokens_details={"cached_tokens": 10},
            completion_tokens_details={"reasoning_tokens": 20}
        )
        
        data = usage.model_dump()
        assert data["prompt_tokens"] == 40
        assert data["completion_tokens"] == 60
        assert data["total_tokens"] == 100
        assert data["prompt_tokens_details"]["cached_tokens"] == 10
        assert data["completion_tokens_details"]["reasoning_tokens"] == 20


class TestChatCompletionResponse:
    """Test ChatCompletionResponse model."""

    def test_basic_response(self):
        """Test basic response creation."""
        response = ChatCompletionResponse(
            id="test-123",
            model="gpt-4",
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message={"role": "assistant", "content": "Hello!"},
                    finish_reason="stop"
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15
            )
        )
        
        assert response.id == "test-123"
        assert response.object == "chat.completion"
        assert response.model == "gpt-4"
        assert len(response.choices) == 1
        assert response.choices[0].message["content"] == "Hello!"
        assert response.usage.total_tokens == 15

    def test_response_with_enhanced_usage(self):
        """Test response with enhanced token usage."""
        response = ChatCompletionResponse(
            id="enhanced-test",
            model="gpt-4o",
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message={"role": "assistant", "content": "Enhanced response"},
                    finish_reason="stop"
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=50,
                completion_tokens=30,
                total_tokens=80,
                prompt_tokens_details={"cached_tokens": 20},
                completion_tokens_details={"reasoning_tokens": 15}
            )
        )
        
        assert response.id == "enhanced-test"
        assert response.usage.prompt_tokens_details["cached_tokens"] == 20
        assert response.usage.completion_tokens_details["reasoning_tokens"] == 15

    def test_multiple_choices(self):
        """Test response with multiple choices."""
        response = ChatCompletionResponse(
            id="multi-choice",
            model="gpt-4",
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message={"role": "assistant", "content": "Option 1"},
                    finish_reason="stop"
                ),
                ChatCompletionChoice(
                    index=1,
                    message={"role": "assistant", "content": "Option 2"},
                    finish_reason="stop"
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=20,
                completion_tokens=10,
                total_tokens=30
            )
        )
        
        assert len(response.choices) == 2
        assert response.choices[0].index == 0
        assert response.choices[1].index == 1
        assert response.choices[0].message["content"] == "Option 1"
        assert response.choices[1].message["content"] == "Option 2"

    def test_response_default_timestamp(self):
        """Test response with default timestamp."""
        before_time = int(time.time())
        
        response = ChatCompletionResponse(
            id="timestamp-test",
            model="gpt-3.5-turbo",
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message={"role": "assistant", "content": "Test"},
                    finish_reason="stop"
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=5,
                completion_tokens=3,
                total_tokens=8
            )
        )
        
        after_time = int(time.time())
        
        assert before_time <= response.created <= after_time

    def test_response_serialization(self):
        """Test complete response serialization."""
        response = ChatCompletionResponse(
            id="serialize-test",
            model="test-model",
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message={"role": "assistant", "content": "Serialization test"},
                    finish_reason="stop"
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=15,
                completion_tokens=10,
                total_tokens=25,
                prompt_tokens_details={"cached_tokens": 5},
                completion_tokens_details={"reasoning_tokens": 3}
            )
        )
        
        # Test JSON serialization
        json_str = json.dumps(response.model_dump())
        assert "serialize-test" in json_str
        assert "Serialization test" in json_str
        assert "cached_tokens" in json_str
        assert "reasoning_tokens" in json_str
        
        # Test deserialization
        data = json.loads(json_str)
        reconstructed = ChatCompletionResponse(**data)
        assert reconstructed.id == response.id
        assert reconstructed.choices[0].message == response.choices[0].message
        assert reconstructed.usage.prompt_tokens_details == response.usage.prompt_tokens_details


class TestErrorModels:
    """Test error response models."""

    def test_error_detail(self):
        """Test ErrorDetail model."""
        error = ErrorDetail(
            message="Test error message",
            type="test_error",
            param="test_param",
            code="TEST_001"
        )
        
        assert error.message == "Test error message"
        assert error.type == "test_error"
        assert error.param == "test_param"
        assert error.code == "TEST_001"

    def test_error_detail_minimal(self):
        """Test ErrorDetail with only required fields."""
        error = ErrorDetail(
            message="Minimal error",
            type="minimal_error"
        )
        
        assert error.message == "Minimal error"
        assert error.type == "minimal_error"
        assert error.param is None
        assert error.code is None

    def test_error_response(self):
        """Test ErrorResponse model."""
        error_response = ErrorResponse(
            error=ErrorDetail(
                message="API error occurred",
                type="api_error",
                code="API_001"
            )
        )
        
        assert error_response.error.message == "API error occurred"
        assert error_response.error.type == "api_error"
        assert error_response.error.code == "API_001"

    def test_error_response_serialization(self):
        """Test error response serialization."""
        error_response = ErrorResponse(
            error=ErrorDetail(
                message="Serialization test error",
                type="serialization_error",
                param="test_field",
                code="SER_001"
            )
        )
        
        data = error_response.model_dump()
        assert data["error"]["message"] == "Serialization test error"
        assert data["error"]["type"] == "serialization_error"
        assert data["error"]["param"] == "test_field"
        assert data["error"]["code"] == "SER_001"


class TestModelValidation:
    """Test model validation and error handling."""

    def test_invalid_choice_missing_required(self):
        """Test validation error for missing required fields."""
        with pytest.raises(ValidationError):
            ChatCompletionChoice(
                # Missing required 'index' and 'message'
                finish_reason="stop"
            )

    def test_invalid_usage_negative_tokens(self):
        """Test that negative token values are accepted (no validation constraint)."""
        # Note: The current model doesn't enforce non-negative constraints
        # This test documents the current behavior
        usage = ChatCompletionUsage(
            prompt_tokens=-5,  # Negative values are currently allowed
            completion_tokens=10,
            total_tokens=5
        )
        
        assert usage.prompt_tokens == -5
        assert usage.completion_tokens == 10
        assert usage.total_tokens == 5

    def test_invalid_response_empty_choices(self):
        """Test that empty choices list is accepted (no validation constraint)."""
        # Note: The current model doesn't enforce non-empty choices
        # This test documents the current behavior
        response = ChatCompletionResponse(
            id="test",
            model="test-model",
            choices=[],  # Empty choices are currently allowed
            usage=ChatCompletionUsage(
                prompt_tokens=5,
                completion_tokens=3,
                total_tokens=8
            )
        )
        
        assert response.choices == []
        assert len(response.choices) == 0

    def test_token_details_type_validation(self):
        """Test that token details accept various dict structures."""
        # Should accept any dict structure for flexibility
        usage = ChatCompletionUsage(
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
            prompt_tokens_details={
                "custom_field": "custom_value",
                "nested": {"inner": 123}
            },
            completion_tokens_details={
                "another_custom": [1, 2, 3]
            }
        )
        
        assert usage.prompt_tokens_details["custom_field"] == "custom_value"
        assert usage.prompt_tokens_details["nested"]["inner"] == 123
        assert usage.completion_tokens_details["another_custom"] == [1, 2, 3]