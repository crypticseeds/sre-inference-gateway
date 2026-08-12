"""Shared helpers for byte-faithful SSE provider streams."""

import logging
from collections.abc import AsyncIterator

import httpx

logger = logging.getLogger(__name__)


async def stream_sse_response(
    response: httpx.Response, provider_name: str
) -> AsyncIterator[bytes]:
    """Yield upstream SSE bytes immediately and always close the response."""
    try:
        async for chunk in response.aiter_bytes():
            yield chunk
    except Exception:
        # Once response bytes have started, retrying would duplicate output and the
        # HTTP status can no longer change. Close cleanly and let missing [DONE]
        # signal the truncated stream to OpenAI-compatible clients.
        logger.exception("Provider %s stream ended unexpectedly", provider_name)
    finally:
        await response.aclose()
