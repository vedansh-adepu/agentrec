"""Tool-call recording and replay for session decorators."""

from __future__ import annotations

import copy
import inspect
import time
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar, cast

from .cassette.model import ErrorRecord
from .errors import ReplayedToolError, ReplayMissError

if TYPE_CHECKING:
    from .session import Session

P = ParamSpec("P")
R = TypeVar("R")


def decorate_tool(session: Session, function: Callable[P, R]) -> Callable[P, R]:
    """Wrap a sync or async tool with pre-execution arguments and replay."""
    signature = inspect.signature(function)

    def arguments(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()
        return copy.deepcopy(dict(bound.arguments))

    if inspect.iscoroutinefunction(function):

        @wraps(function)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            snapshot = arguments(args, kwargs)
            request = {"name": function.__name__, "arguments": snapshot}
            key = session.match_policy.tool_key(function.__name__, snapshot)
            played = session._lookup(key, request)
            if played is not None:
                if played.error:
                    raise ReplayedToolError(played.error.type, played.error.message)
                if played.response is None:
                    raise ReplayMissError("recorded tool interaction has no result")
                return copy.deepcopy(played.response["result"])
            if not session._recording_allowed():
                raise ReplayMissError(f"tool replay miss: {function.__name__}")
            started = datetime.now(UTC)
            tick = time.perf_counter()
            try:
                result = await function(*args, **kwargs)
            except Exception as exc:
                session._append(
                    "tool",
                    key,
                    request,
                    None,
                    ErrorRecord(type=type(exc).__name__, message=str(exc)),
                    started,
                    (time.perf_counter() - tick) * 1000,
                )
                raise
            session._append(
                "tool",
                key,
                request,
                {"result": copy.deepcopy(result)},
                None,
                started,
                (time.perf_counter() - tick) * 1000,
            )
            return result

        return cast(Callable[P, R], async_wrapper)

    @wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
        snapshot = arguments(args, kwargs)
        request = {"name": function.__name__, "arguments": snapshot}
        key = session.match_policy.tool_key(function.__name__, snapshot)
        played = session._lookup(key, request)
        if played is not None:
            if played.error:
                raise ReplayedToolError(played.error.type, played.error.message)
            if played.response is None:
                raise ReplayMissError("recorded tool interaction has no result")
            return copy.deepcopy(played.response["result"])
        if not session._recording_allowed():
            raise ReplayMissError(f"tool replay miss: {function.__name__}")
        started = datetime.now(UTC)
        tick = time.perf_counter()
        try:
            result = function(*args, **kwargs)
        except Exception as exc:
            session._append(
                "tool",
                key,
                request,
                None,
                ErrorRecord(type=type(exc).__name__, message=str(exc)),
                started,
                (time.perf_counter() - tick) * 1000,
            )
            raise
        session._append(
            "tool",
            key,
            request,
            {"result": copy.deepcopy(result)},
            None,
            started,
            (time.perf_counter() - tick) * 1000,
        )
        return result

    return wrapper
