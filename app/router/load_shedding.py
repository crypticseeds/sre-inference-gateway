"""Immediate concurrency admission for gateway and provider work."""

import asyncio
from collections.abc import AsyncIterator, Callable
from typing import Any

from starlette.responses import StreamingResponse

from app.config.models import LoadSheddingConfig


class AdmissionLease:
    """An idempotently releasable semaphore permit."""

    def __init__(self, release: Callable[[], None]):
        self._release = release
        self._released = False

    def release(self) -> None:
        """Return the permit once."""
        if not self._released:
            self._released = True
            self._release()


class AdmissionStream:
    """Hold admission leases until a stream ends or closes."""

    def __init__(self, stream: AsyncIterator[bytes], *leases: AdmissionLease):
        self._stream = stream
        self._leases = leases

    def __aiter__(self) -> "AdmissionStream":
        return self

    async def __anext__(self) -> bytes:
        try:
            return await anext(self._stream)
        except BaseException:
            self._release()
            raise

    async def aclose(self) -> None:
        """Close the wrapped stream and always return capacity."""
        close = getattr(self._stream, "aclose", None)
        try:
            if close is not None:
                await close()
        finally:
            self._release()

    def _release(self) -> None:
        for lease in self._leases:
            lease.release()


class AdmissionStreamingResponse(StreamingResponse):
    """Ensure admission is released across the complete ASGI response lifecycle."""

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            close = getattr(self.body_iterator, "aclose", None)
            if close is not None:
                await close()


class LoadShedder:
    """Enforce configured concurrency limits without queueing."""

    def __init__(self) -> None:
        self.configure(LoadSheddingConfig())

    def configure(self, config: LoadSheddingConfig) -> None:
        """Apply configuration; intended for startup before serving requests."""
        self.enabled = config.enabled
        self._global = asyncio.Semaphore(config.global_max_in_flight)
        self._per_provider_limit = config.per_provider_max_in_flight
        self._providers: dict[str, asyncio.Semaphore] = {}

    @staticmethod
    async def _try_acquire(semaphore: asyncio.Semaphore) -> AdmissionLease | None:
        # There is no await between the capacity check and acquire, so admission is
        # atomic on the event loop and never joins the semaphore's waiter queue.
        if semaphore.locked():
            return None
        await semaphore.acquire()
        return AdmissionLease(semaphore.release)

    async def try_acquire_global(self) -> AdmissionLease | None:
        """Acquire gateway capacity immediately, or return None."""
        if not self.enabled:
            return AdmissionLease(lambda: None)
        return await self._try_acquire(self._global)

    def provider_has_capacity(self, provider: str) -> bool:
        """Return whether routing may currently select a provider."""
        if not self.enabled:
            return True
        semaphore = self._providers.get(provider)
        return semaphore is None or not semaphore.locked()

    async def try_acquire_provider(self, provider: str) -> AdmissionLease | None:
        """Acquire provider capacity immediately, or return None."""
        if not self.enabled:
            return AdmissionLease(lambda: None)
        semaphore = self._providers.setdefault(
            provider, asyncio.Semaphore(self._per_provider_limit)
        )
        return await self._try_acquire(semaphore)


load_shedder = LoadShedder()
