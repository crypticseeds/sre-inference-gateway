"""Chat completions API endpoint implementation."""

import logging
import time
from typing import Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Request, status
from opentelemetry import trace
from starlette.responses import StreamingResponse

from app.api.dependencies import (
    get_provider_priority,
    get_request_id,
    get_router,
    setup_request_context,
)
from app.models.requests import ChatCompletionRequest
from app.models.responses import ChatCompletionResponse
from app.observability.metrics import (
    IN_FLIGHT_REQUESTS,
    instrument_stream,
    record_failure,
    record_request,
    record_request_duration,
    record_shed,
    record_usage,
)
from app.router.load_shedding import (
    AdmissionLease,
    AdmissionStream,
    AdmissionStreamingResponse,
    load_shedder,
)
from app.router.router import RequestRouter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/chat/completions",
    response_model=ChatCompletionResponse,
    status_code=status.HTTP_200_OK,
    summary="Create chat completion",
    description="Creates a model response for the given chat conversation.",
)
async def create_chat_completion(
    request: Request,
    chat_request: ChatCompletionRequest,
    request_id: str = Depends(get_request_id),
    provider_priority: Optional[str] = Depends(get_provider_priority),
    request_router: RequestRouter = Depends(get_router),
    _: None = Depends(setup_request_context),
) -> Union[ChatCompletionResponse, StreamingResponse]:
    """Create a chat completion.

    Args:
        request: FastAPI request object
        chat_request: Chat completion request
        request_id: Request ID
        provider_priority: Optional provider priority
        request_router: Request router instance

    Returns:
        Chat completion response

    Raises:
        HTTPException: If no providers available or provider error
    """
    span = trace.get_current_span()
    global_lease = await load_shedder.try_acquire_global()
    if global_lease is None:
        record_shed("global")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gateway concurrency limit reached; retry later",
            headers={"Retry-After": "1"},
        )

    try:
        # Convert to base model format for provider compatibility
        from app.providers.base import ChatCompletionRequest as BaseRequest

        base_request = BaseRequest(
            model=chat_request.model,
            messages=[msg.model_dump() for msg in chat_request.messages],
            temperature=chat_request.temperature,
            max_tokens=chat_request.max_tokens,
            max_completion_tokens=chat_request.max_completion_tokens,
            top_p=chat_request.top_p,
            frequency_penalty=chat_request.frequency_penalty,
            presence_penalty=chat_request.presence_penalty,
            stream=chat_request.stream,
            stream_options=chat_request.stream_options,
            user=chat_request.user,
        )

        attempted_providers = set()
        last_provider_error = None

        while provider := request_router.select_provider(
            provider_priority, attempted_providers
        ):
            attempted_providers.add(provider.name)
            provider_lease = await load_shedder.try_acquire_provider(provider.name)
            if provider_lease is None:
                continue

            if span:
                span.set_attribute("provider.name", provider.name)
                span.set_attribute("chat.model", chat_request.model)
                span.set_attribute("chat.stream", chat_request.stream)
                span.set_attribute("chat.messages_count", len(chat_request.messages))

            logger.info(
                f"Processing request {request_id} with provider {provider.name} "
                f"for model {chat_request.model}"
            )

            started_at = time.monotonic()
            in_flight = IN_FLIGHT_REQUESTS.labels(provider=provider.name)
            in_flight.inc()
            in_flight_lease = AdmissionLease(in_flight.dec)
            try:
                if chat_request.stream:
                    stream = await provider.chat_completion_stream(
                        base_request, request_id
                    )
                    response = AdmissionStreamingResponse(
                        AdmissionStream(
                            instrument_stream(
                                stream,
                                provider.name,
                                chat_request.model,
                                started_at,
                                account_in_flight=False,
                            ),
                            global_lease,
                            provider_lease,
                            in_flight_lease,
                        ),
                        media_type="text/event-stream",
                        headers={
                            "Cache-Control": "no-cache",
                            "X-Accel-Buffering": "no",
                        },
                    )
                    global_lease = None
                    provider_lease = None
                    in_flight_lease = None
                    return response

                response = await provider.chat_completion(base_request, request_id)
                record_usage(provider.name, chat_request.model, response.usage)
                record_request(provider.name, chat_request.model, False, 200)
                record_request_duration(provider.name, False, started_at)
                logger.info(f"Completed request {request_id} successfully")
                return response
            except HTTPException as error:
                record_request(
                    provider.name,
                    chat_request.model,
                    chat_request.stream,
                    error.status_code,
                )
                record_request_duration(
                    provider.name, chat_request.stream, started_at
                )
                record_failure(
                    provider.name,
                    "client_4xx"
                    if 400 <= error.status_code < 500 and error.status_code != 429
                    else "establishment",
                )
                if error.status_code < 500:
                    raise
                last_provider_error = error
                logger.warning(
                    "event=provider_failover request_id=%s failed_provider=%s "
                    "status_code=%s",
                    request_id,
                    provider.name,
                    error.status_code,
                )
            except Exception:
                record_request(provider.name, chat_request.model, chat_request.stream, 500)
                record_request_duration(
                    provider.name, chat_request.stream, started_at
                )
                record_failure(provider.name, "establishment")
                raise
            finally:
                if in_flight_lease is not None:
                    in_flight_lease.release()
                if provider_lease is not None:
                    provider_lease.release()

        if last_provider_error:
            raise last_provider_error

        logger.error(f"No available providers for request {request_id}")
        saturated = request_router.get_saturated_providers()
        if saturated:
            record_shed("provider", saturated[0])
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="All eligible inference providers are at capacity; retry later",
                headers={"Retry-After": "1"},
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No inference providers available",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request {request_id}: {str(e)}")
        if span:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
    finally:
        if global_lease is not None:
            global_lease.release()
