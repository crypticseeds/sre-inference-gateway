"""OpenAI adapter implementation."""

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


class OpenAIAdapter(BaseProvider):
    """OpenAI API adapter implementation.

    This provider integrates with the OpenAI API to handle chat completion
    requests. It includes retry logic, error handling, and health monitoring.

    Attributes:
        name: Provider identifier
        config: Provider configuration dictionary
        api_key: OpenAI API authentication key
        base_url: OpenAI API base URL
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts for failed requests
        client: Async HTTP client for API requests

    Example:
        ```python
        adapter = OpenAIAdapter(
            name="openai-gpt4",
            config={"model": "gpt-4"},
            api_key="sk-...",
            base_url="https://api.openai.com/v1",
            timeout=30.0,
            max_retries=3
        )

        request = ChatCompletionRequest(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello!"}]
        )

        response = await adapter.chat_completion(request, "req-123")
        ```
    """

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        name: str,
        config: Dict[str, Any],
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """Initialize OpenAI provider.

        Args:
            name: Provider name for identification and logging
            config: Provider configuration dictionary
            api_key: OpenAI API key for authentication
            base_url: OpenAI API base URL (default: https://api.openai.com/v1)
            timeout: Request timeout in seconds (default: 30.0)
            max_retries: Maximum number of retry attempts (default: 3)
        """
        super().__init__(name, config)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        # Create httpx client with timeout configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    # pylint: disable=too-many-branches,too-many-statements
    async def chat_completion(
        self,
        request: ChatCompletionRequest,
        request_id: str,
    ) -> ChatCompletionResponse:
        """Process chat completion request via OpenAI API.

        Sends a chat completion request to the OpenAI API with automatic
        retry logic for transient failures. Implements exponential backoff
        for rate limits and server errors.

        Args:
            request: Chat completion request containing model, messages, and parameters
            request_id: Unique identifier for request tracking and logging

        Returns:
            ChatCompletionResponse containing the model's response, usage stats,
            and metadata

        Raises:
            HTTPException: On authentication errors (401), invalid requests (400),
                rate limits (429), server errors (5xx), or timeout

        Example:
            ```python
            request = ChatCompletionRequest(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "Hello!"}
                ],
                temperature=0.7,
                max_tokens=100
            )

            response = await provider.chat_completion(request, "req-abc123")
            print(response.choices[0]["message"]["content"])
            ```
        """
        start_time = time.time()

        try:
            # Prepare request payload
            payload = {
                "model": request.model,
                "messages": request.messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "top_p": request.top_p,
                "frequency_penalty": request.frequency_penalty,
                "presence_penalty": request.presence_penalty,
                "stream": request.stream,
            }

            # Remove None values
            payload = {k: v for k, v in payload.items() if v is not None}

            if request.user:
                payload["user"] = request.user

            # Make API request with retries
            for attempt in range(self.max_retries):
                try:
                    logger.debug(
                        "OpenAI request attempt %d/%d: request_id=%s, model=%s",
                        attempt + 1,
                        self.max_retries,
                        request_id,
                        request.model,
                    )

                    response = await self.client.post(
                        f"{self.base_url}/chat/completions",
                        json=payload,
                    )
                    response.raise_for_status()

                    # Parse response
                    data = response.json()

                    elapsed_ms = (time.time() - start_time) * 1000
                    logger.info(
                        "OpenAI request successful: request_id=%s, elapsed=%.2fms",
                        request_id,
                        elapsed_ms,
                    )

                    # Convert to our response model
                    return ChatCompletionResponse(
                        id=data.get("id", request_id),
                        created=data.get("created", int(time.time())),
                        model=data.get("model", request.model),
                        choices=data.get("choices", []),
                        usage=data.get("usage", {}),
                    )

                except httpx.HTTPStatusError as e:
                    status_code = e.response.status_code

                    logger.warning(
                        "OpenAI API error (attempt %d/%d): %d - %s",
                        attempt + 1,
                        self.max_retries,
                        status_code,
                        e.response.text,
                    )

                    # Don't retry on client errors (4xx) except rate limits
                    if 400 <= status_code < 500 and status_code != 429:
                        if status_code == 401:
                            raise HTTPException(
                                status_code=500,
                                detail="OpenAI API authentication failed",
                            ) from e
                        if status_code == 400:
                            # FIX: Guard against malformed JSON responses
                            try:
                                error_data = e.response.json()
                                error_msg = error_data.get("error", {}).get(
                                    "message", "Unknown error"
                                )
                            except (ValueError, KeyError):
                                # Fallback to text if JSON parsing fails
                                error_msg = e.response.text or "Invalid request format"
                            raise HTTPException(
                                status_code=400, detail=f"Invalid request: {error_msg}"
                            ) from e
                        raise HTTPException(
                            status_code=status_code,
                            detail=f"OpenAI API error: {e.response.text}",
                        ) from e

                    # Exponential backoff for retries
                    if attempt < self.max_retries - 1:
                        backoff_time = 2**attempt
                        logger.info("Retrying after %ds backoff", backoff_time)
                        await asyncio.sleep(backoff_time)
                        continue

                    # Last attempt failed
                    if status_code == 429:
                        raise HTTPException(
                            status_code=429, detail="OpenAI API rate limit exceeded"
                        ) from e
                    raise HTTPException(
                        status_code=502, detail="OpenAI API server error"
                    ) from e

                except httpx.TimeoutException as timeout_exc:
                    logger.warning(
                        "OpenAI API timeout (attempt %d/%d)",
                        attempt + 1,
                        self.max_retries,
                    )

                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    raise HTTPException(
                        status_code=504, detail="OpenAI API request timeout"
                    ) from timeout_exc

                except httpx.RequestError as req_err:
                    elapsed_ms = (time.time() - start_time) * 1000
                    logger.error(
                        "OpenAI request error (attempt %d/%d): %s. "
                        "Request ID: %s, Elapsed: %.2fms",
                        attempt + 1,
                        self.max_retries,
                        req_err,
                        request_id,
                        elapsed_ms,
                    )

                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    raise HTTPException(
                        status_code=502,
                        detail=f"Failed to connect to OpenAI API: {str(req_err)}",
                    ) from req_err

            # Note: This point is unreachable - the loop always returns on success
            # or raises an exception on final failure. This is intentional as all
            # error handling and logging is done inside the loop's exception handlers.

        except HTTPException:
            # Re-raise HTTPExceptions as-is
            raise

    async def health_check(self) -> ProviderHealth:
        """Check OpenAI API health and measure latency.

        Performs a lightweight health check by querying the OpenAI models
        endpoint. Measures response latency for monitoring.

        Returns:
            ProviderHealth object containing:
                - name: Provider identifier
                - healthy: Boolean health status
                - latency_ms: Response latency in milliseconds
                - error: Error message if unhealthy (optional)

        Example:
            ```python
            health = await provider.health_check()
            if health.healthy:
                print(f"Provider healthy, latency: {health.latency_ms}ms")
            else:
                print(f"Provider unhealthy: {health.error}")
            ```
        """
        start_time = time.time()

        try:
            # Use models endpoint for health check
            response = await self.client.get(
                f"{self.base_url}/models",
                timeout=5.0,
            )
            response.raise_for_status()

            latency_ms = (time.time() - start_time) * 1000

            logger.debug("OpenAI health check passed: latency=%.2fms", latency_ms)

            return ProviderHealth(
                name=self.name,
                healthy=True,
                latency_ms=latency_ms,
            )

        except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException) as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("OpenAI health check failed: %s", str(e))

            return ProviderHealth(
                name=self.name,
                healthy=False,
                latency_ms=latency_ms,
                error=str(e),
            )

    async def close(self) -> None:
        """Close the HTTP client connection.

        Properly closes the underlying httpx AsyncClient to release resources.
        Should be called when the provider is no longer needed.

        Example:
            ```python
            adapter = OpenAIAdapter(...)
            try:
                # Use adapter
                response = await adapter.chat_completion(...)
            finally:
                await adapter.close()
            ```
        """
        await self.client.aclose()
        logger.debug("OpenAI provider '%s' client closed", self.name)
