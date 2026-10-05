"""Streaming byte-stream helpers for event-stream responses."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator

import httpx2


class RecordingStream(httpx2.SyncByteStream):
    """Forward chunks progressively and report the complete byte sequence."""

    def __init__(self, source: httpx2.Response, done: Callable[[bytes], None]) -> None:
        self.source = source
        self.done = done
        self._chunks: list[bytes] = []
        self._completed = False

    def __iter__(self) -> Iterator[bytes]:
        """Yield upstream chunks without buffering them before the caller."""
        for chunk in self.source.iter_bytes():
            self._chunks.append(chunk)
            yield chunk
        if not self._completed:
            self._completed = True
            self.done(b"".join(self._chunks))

    def close(self) -> None:
        """Drain an early-closed stream before recording its complete body."""
        if not self._completed:
            self._chunks.extend(self.source.iter_bytes())
            self._completed = True
            self.done(b"".join(self._chunks))
        self.source.close()


class AsyncRecordingStream(httpx2.AsyncByteStream):
    """Forward async chunks progressively and report the complete body."""

    def __init__(self, source: httpx2.Response, done: Callable[[bytes], None]) -> None:
        self.source = source
        self.done = done
        self._chunks: list[bytes] = []
        self._completed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        """Yield upstream async chunks without consuming them first."""
        async for chunk in self.source.aiter_bytes():
            self._chunks.append(chunk)
            yield chunk
        if not self._completed:
            self._completed = True
            self.done(b"".join(self._chunks))

    async def aclose(self) -> None:
        """Drain an early-closed async stream before recording its complete body."""
        if not self._completed:
            async for chunk in self.source.aiter_bytes():
                self._chunks.append(chunk)
            self._completed = True
            self.done(b"".join(self._chunks))
        await self.source.aclose()
