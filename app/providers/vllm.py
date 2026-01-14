"""vLLM adapter implementation.

This module provides an adapter for vLLM inference services that expose an
OpenAI-compatible API. The adapter translates internal BaseProvider interface
calls to vLLM API requests, handling retries, error handling, and health monitoring.
"""

import asyncio
import logging
import time
from typing import Any, Dict

import httpx
from fastapi import HTTPException

from app.providers.base import (
    BaseProvider,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ProviderHealth,
)

logger = logging.getLogger(__name__)


class VLLMAdapter(BaseProvider):
    """vLLM inference service adapter implementation."""

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        name: str,
        config: Dict[str, Any],
        base_url: str = "http://localhost:8000/v1",
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """Initialize vLLM adapter."""
        super().__init__(name, config)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        # Create httpx client with timeout configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={"Content-Type": "application/json"},
        )

    # pylint: disable=too-many-branches
    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        request_id: str,
    ) -> ChatCompletionResponse:
        """Process chat completion request via vLLM service."""
        url = f"{self.base_url}/chat/completions"

        # Convert request to dict for API call
        payload = request.model_dump(exclude_none=True)

        # Implement retry logic with exponential backoff
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    "vLLM request attempt %d/%d: request_id=%s, model=%s",
                    attempt + 1,
                    self.max_retries,
                    request_id,
                    request.model,
                )

                response = await self.client.post(url, json=payload)

                # Handle different HTTP status codes
                if response.status_code == 200:
                    data = response.json()
                    return ChatCompletionResponse(**data)

                if response.status_code == 400:
                    # FIX: Guard against malformed JSON responses
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get(
                            "message", "Unknown error"
                        )
                    except (ValueError, Exception):
                        # Fallback to text if JSON parsing fails
                        error_msg = response.text or "Invalid request format"
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid request: {error_msg}",
                    )

                if response.status_code == 503:
                    # Service unavailable - retry with exponential backoff
                    logger.warning(
                        "vLLM service unavailable, attempt %d/%d",
                        attempt + 1,
                        self.max_retries,
                    )
                    if attempt < self.max_retries - 1:
                        # FIX: Add exponential backoff delay
                        backoff_time = 2**attempt
                        await asyncio.sleep(backoff_time)
                        continue
                    raise HTTPException(
                        status_code=503,
                        detail="vLLM service unavailable",
                    )

                if response.status_code >= 500:
                    # Server error - retry with exponential backoff
                    logger.warning(
                        "vLLM server error %d, attempt %d/%d",
                        response.status_code,
                        attempt + 1,
                        self.max_retries,
                    )
                    if attempt < self.max_retries - 1:
                        # FIX: Add exponential backoff delay
                        backoff_time = 2**attempt
                        await asyncio.sleep(backoff_time)
                        continue
                    raise HTTPException(
                        status_code=502,
                        detail="vLLM service error",
                    )

                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"vLLM API error: {response.text}",
                )

            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(
                    "vLLM request timeout, attempt %d/%d",
                    attempt + 1,
                    self.max_retries,
                )
                if attempt < self.max_retries - 1:
                    # FIX: Add exponential backoff delay
                    backoff_time = 2**attempt
                    await asyncio.sleep(backoff_time)
                    continue
                raise HTTPException(
                    status_code=504,
                    detail="vLLM service request timeout",
                ) from e

            except httpx.RequestError as e:
                last_exception = e
                logger.error("vLLM request error: %s", e)
                if attempt < self.max_retries - 1:
                    # FIX: Add exponential backoff delay
                    backoff_time = 2**attempt
                    await asyncio.sleep(backoff_time)
                    continue
                raise HTTPException(
                    status_code=502,
                    detail=f"Failed to connect to vLLM service: {str(e)}",
                ) from e

        # If we exhausted retries
        if last_exception:
            logger.error("vLLM request failed with last exception: %s", last_exception)
        raise HTTPException(
            status_code=502,
            detail=f"vLLM service request failed after {self.max_retries} attempts",
        )

    async def health_check(self) -> ProviderHealth:
        """Check vLLM service health and measure latency."""
        start_time = time.time()

        try:
            # Use models endpoint for health check
            url = f"{self.base_url}/models"
            response = await self.client.get(url, timeout=5.0)

            latency_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                return ProviderHealth(
                    name=self.name,
                    healthy=True,
                    latency_ms=latency_ms,
                )

            return ProviderHealth(
                name=self.name,
                healthy=False,
                latency_ms=latency_ms,
                error=f"HTTP {response.status_code}",
            )

        except (httpx.TimeoutException, httpx.RequestError) as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("vLLM health check failed: %s", e)
            return ProviderHealth(
                name=self.name,
                healthy=False,
                latency_ms=latency_ms,
                error=str(e),
            )

    async def close(self) -> None:
        """Close HTTP client connection and release resources."""
        await self.client.aclose()
