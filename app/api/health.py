"""Health check endpoints with provider monitoring."""

import asyncio
import logging
import time
from typing import Dict, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_router
from app.config.settings import get_gateway_config
from app.router.resilience import resilience_registry
from app.router.router import RequestRouter

logger = logging.getLogger(__name__)
router = APIRouter()

# Global health status cache
_provider_health_cache: Dict[str, Dict] = {}
_last_health_check: float = 0
_health_check_lock = asyncio.Lock()


async def check_provider_health(
    provider_name: str, health_url: Optional[str], timeout: float = 5.0
) -> Dict:
    """Check health of a single provider.

    Args:
        provider_name: Name of the provider
        health_url: Health check URL (optional)
        timeout: Request timeout in seconds

    Returns:
        Health status dictionary
    """
    health_status = {
        "name": provider_name,
        "status": "unknown",
        "response_time": None,
        "error": None,
        "last_check": time.time(),
    }

    if not health_url:
        # If no health URL provided, assume healthy if provider is registered
        health_status["status"] = "healthy"
        health_status["response_time"] = 0.0
        return health_status

    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(health_url)
            response_time = time.time() - start_time

            if response.status_code == 200:
                health_status.update(
                    {
                        "status": "healthy",
                        "response_time": response_time,
                    }
                )
            else:
                health_status.update(
                    {
                        "status": "unhealthy",
                        "response_time": response_time,
                        "error": f"HTTP {response.status_code}",
                    }
                )

    except httpx.TimeoutException:
        health_status.update(
            {
                "status": "unhealthy",
                "response_time": time.time() - start_time,
                "error": "Timeout",
            }
        )
    except Exception as e:
        health_status.update(
            {
                "status": "unhealthy",
                "response_time": time.time() - start_time,
                "error": str(e),
            }
        )

    return health_status


async def update_provider_health_cache() -> None:
    """Update the provider health cache."""
    global _provider_health_cache, _last_health_check

    async with _health_check_lock:
        config = get_gateway_config()
        current_time = time.time()

        # Check if we need to update (based on check interval)
        if (current_time - _last_health_check) < config.health.check_interval:
            return

        logger.debug("Updating provider health cache")

        # Check health for all configured providers
        health_tasks = []
        for provider_config in config.providers:
            if provider_config.enabled:
                task = check_provider_health(
                    provider_config.name,
                    provider_config.health_check_url,
                    config.health.timeout,
                )
                health_tasks.append(task)

        if health_tasks:
            health_results = await asyncio.gather(*health_tasks, return_exceptions=True)

            for result in health_results:
                if isinstance(result, Exception):
                    logger.error(f"Health check failed: {result}")
                    continue

                _provider_health_cache[result["name"]] = result

        _last_health_check = current_time
        logger.debug(
            f"Updated health cache for {len(_provider_health_cache)} providers"
        )


@router.get("/health")
async def health_check() -> Dict:
    """Basic health check endpoint.

    Returns:
        Basic health status
    """
    return {
        "status": "healthy",
        "service": "sre-inference-gateway",
        "timestamp": time.time(),
    }


@router.get("/health/detailed")
async def detailed_health_check() -> Dict:
    """Detailed health check with provider status.

    Returns:
        Detailed health status including provider information
    """
    # Update health cache
    await update_provider_health_cache()

    config = get_gateway_config()
    enabled_providers = config.get_enabled_providers()

    # Calculate overall status by checking enabled providers against cache
    healthy_providers = 0
    for provider in enabled_providers:
        # Check cache for this provider's health status
        provider_health = _provider_health_cache.get(provider.name, {})
        if provider_health.get("status") == "healthy":
            healthy_providers += 1

    total_providers = len(enabled_providers)

    # Determine overall status
    if total_providers == 0:
        overall_status = "unhealthy"
    elif healthy_providers == 0:
        overall_status = "unhealthy"
    elif healthy_providers < total_providers:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    # Filter provider details to only include enabled providers
    enabled_provider_names = {provider.name for provider in enabled_providers}
    filtered_details = [
        health
        for health in _provider_health_cache.values()
        if health["name"] in enabled_provider_names
    ]

    return {
        "status": overall_status,
        "service": "sre-inference-gateway",
        "timestamp": time.time(),
        "providers": {
            "total": total_providers,
            "healthy": healthy_providers,
            "unhealthy": total_providers - healthy_providers,
            "details": filtered_details,
        },
        "configuration": {
            "version": config.version,
            "health_check_interval": config.health.check_interval,
            "last_health_check": _last_health_check,
        },
    }


@router.get("/ready")
async def readiness_check(request_router: RequestRouter = Depends(get_router)) -> Dict:
    """Readiness check endpoint with provider availability.

    Args:
        request_router: Request router instance

    Returns:
        Readiness status with available providers

    Raises:
        HTTPException: If no providers are available (503 Service Unavailable)
    """
    # Update health cache
    await update_provider_health_cache()

    available_providers = request_router.get_available_providers()

    # Get healthy providers from cache
    healthy_providers = []
    if _provider_health_cache:
        # Use health cache if available
        healthy_providers = [
            name
            for name, health in _provider_health_cache.items()
            if health["status"] == "healthy" and name in available_providers
        ]
    else:
        # Fall back to router's available providers if no health data
        healthy_providers = available_providers

    is_ready = len(healthy_providers) > 0

    response_data = {
        "status": "ready" if is_ready else "not_ready",
        "available_providers": available_providers,
        "healthy_providers": healthy_providers,
        "provider_count": len(available_providers),
        "healthy_count": len(healthy_providers),
        "timestamp": time.time(),
    }

    # Return 503 if no healthy providers are available
    if not is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=response_data
        )

    return response_data


@router.get("/health/providers")
async def provider_health_status() -> Dict:
    """Get detailed provider health status.

    Returns:
        Provider health status details
    """
    # Update health cache
    await update_provider_health_cache()

    return {
        "providers": list(_provider_health_cache.values()),
        "last_updated": _last_health_check,
        "timestamp": time.time(),
    }


@router.get("/health/circuit-breakers")
async def circuit_breaker_status() -> Dict:
    """Get circuit breaker status for all providers.

    Returns:
        Circuit breaker status for all providers
    """
    circuit_breaker_states = resilience_registry.get_all_circuit_breaker_states()

    return {
        "circuit_breakers": circuit_breaker_states,
        "timestamp": time.time(),
    }


@router.get("/health/circuit-breakers/{provider_name}")
async def single_provider_circuit_breaker(provider_name: str) -> Dict:
    """Get circuit breaker status for a specific provider.

    Args:
        provider_name: Name of the provider

    Returns:
        Circuit breaker status for the provider

    Raises:
        HTTPException: If provider not found (404)
    """
    circuit_breaker_states = resilience_registry.get_all_circuit_breaker_states()

    if provider_name not in circuit_breaker_states:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Circuit breaker for provider '{provider_name}' not found",
        )

    return {
        "circuit_breaker": circuit_breaker_states[provider_name],
        "timestamp": time.time(),
    }


@router.get("/health/providers/{provider_name}")
async def single_provider_health(provider_name: str) -> Dict:
    """Get health status for a specific provider.

    Args:
        provider_name: Name of the provider

    Returns:
        Provider health status

    Raises:
        HTTPException: If provider not found (404)
    """
    # Update health cache
    await update_provider_health_cache()

    if provider_name not in _provider_health_cache:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_name}' not found",
        )

    return _provider_health_cache[provider_name]
