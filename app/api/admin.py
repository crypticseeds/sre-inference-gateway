"""Runtime controls for no-key mock provider drills."""

import logging
import os
from typing import Dict

from fastapi import APIRouter, HTTPException, status

from app.providers.mock import MockOpenAIAdapter, MockVLLMAdapter
from app.providers.registry import provider_registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/providers")


def _set_mock_failure(provider_name: str, failed: bool) -> Dict[str, object]:
    """Set failure injection state for a registered mock provider."""
    if os.getenv("FAILOVER_DRILL_ADMIN") != "1":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    provider = provider_registry.get_provider(provider_name)
    if not isinstance(provider, (MockOpenAIAdapter, MockVLLMAdapter)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mock provider '{provider_name}' not found",
        )

    provider.set_failed(failed)
    logger.warning(
        "event=mock_provider_failure provider=%s failed=%s",
        provider_name,
        str(failed).lower(),
    )
    return {"provider": provider_name, "failed": failed}


@router.post("/{provider_name}/fail")
async def fail_mock_provider(provider_name: str) -> Dict[str, object]:
    """Make a mock provider fail new requests before response headers."""
    return _set_mock_failure(provider_name, True)


@router.post("/{provider_name}/restore")
async def restore_mock_provider(provider_name: str) -> Dict[str, object]:
    """Restore a failed mock provider."""
    return _set_mock_failure(provider_name, False)
