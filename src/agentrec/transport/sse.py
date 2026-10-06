"""Streaming byte-stream helpers for event-stream responses."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator

import httpx2


class RecordingStream(httpx2.SyncByteStream):
    """Forward chunks progressively and report the complete byte sequence."""

    def __init__(
        self,
        source: httpx2.Response,
        done: Callable[[bytes], None],
        failed: Callable[[httpx2.RequestError], None] | None = None,
    ) -> None:
        self.source = source
        self.done = done
        self.failed = failed
        self._chunks: list[bytes] = []
        self._completed = False
        self._iterator = source.iter_bytes()

    def __iter__(self) -> Iterator[bytes]:
        """Yield decoded chunks progressively and record transport failures."""
        try:
            for chunk in self._iterator:
                self._chunks.append(chunk)
                yield chunk
        except httpx2.RequestError as exc:
            self._completed = True
            if self.failed is not None:
                self.failed(exc)
            raise
        if not self._completed:
            self._completed = True
            self.done(b"".join(self._chunks))

    def close(self) -> None:
        """Drain an early close through the same iterator and close upstream."""
        try:
            if not self._completed:
                for _chunk in self:
                    pass
        finally:
            self.source.close()


class AsyncRecordingStream(httpx2.AsyncByteStream):
    """Forward async chunks progressively and report the complete body."""

    def __init__(
        self,
        source: httpx2.Response,
        done: Callable[[bytes], None],
        failed: Callable[[httpx2.RequestError], None] | None = None,
    ) -> None:
        self.source = source
        self.done = done
        self.failed = failed
        self._chunks: list[bytes] = []
        self._completed = False
        self._iterator = source.aiter_bytes()

    async def __aiter__(self) -> AsyncIterator[bytes]:
        """Yield decoded async chunks progressively and record failures."""
        try:
            async for chunk in self._iterator:
                self._chunks.append(chunk)
                yield chunk
        except httpx2.RequestError as exc:
            self._completed = True
            if self.failed is not None:
                self.failed(exc)
            raise
        if not self._completed:
            self._completed = True
            self.done(b"".join(self._chunks))

    async def aclose(self) -> None:
        """Drain an early async close through the same iterator, then close upstream."""
        try:
            if not self._completed:
                async for _chunk in self:
                    pass
        finally:
            await self.source.aclose()
