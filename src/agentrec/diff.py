"""Step-level trajectory comparison for schema-v2 cassettes."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _short(value: Any, limit: int = 100) -> str:
    rendered = repr(value)
    return rendered if len(rendered) <= limit else rendered[: limit - 3] + "..."


def _path_diffs(
    left: Any, right: Any, path: str = "", *, limit: int = 10
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []

    def walk(a: Any, b: Any, current: str) -> None:
        if len(result) >= limit:
            return
        if isinstance(a, dict) and isinstance(b, dict):
            for key in sorted(a.keys() | b.keys()):
                escaped = str(key).replace("~", "~0").replace("/", "~1")
                child = f"{current}/{escaped}"
                if key not in a:
                    result.append(
                        {"path": child, "left": "<missing>", "right": _short(b[key])}
                    )
                elif key not in b:
                    result.append(
                        {"path": child, "left": _short(a[key]), "right": "<missing>"}
                    )
                else:
                    walk(a[key], b[key], child)
                if len(result) >= limit:
                    return
        elif isinstance(a, list) and isinstance(b, list):
            for index in range(max(len(a), len(b))):
                child = f"{current}/{index}"
                if index >= len(a):
                    result.append(
                        {"path": child, "left": "<missing>", "right": _short(b[index])}
                    )
                elif index >= len(b):
                    result.append(
                        {"path": child, "left": _short(a[index]), "right": "<missing>"}
                    )
                else:
                    walk(a[index], b[index], child)
                if len(result) >= limit:
                    return
        elif a != b:
            result.append(
                {"path": current or "/", "left": _short(a), "right": _short(b)}
            )

    walk(left, right, path)
    return result


def _identity(item: Any) -> tuple[str, str, int]:
    return item.kind, item.key, item.occurrence


def _step_diff(left: Any, right: Any) -> dict[str, Any]:
    left_name = (
        left.request.get("name")
        if left.kind == "tool"
        else (f"{left.request.get('method')} {left.request.get('url')}")
    )
    right_name = (
        right.request.get("name")
        if right.kind == "tool"
        else (f"{right.request.get('method')} {right.request.get('url')}")
    )
    request_paths = _path_diffs(left.request, right.request)
    response_paths = _path_diffs(left.response, right.response)
    error_paths = _path_diffs(
        left.error.model_dump() if left.error else None,
        right.error.model_dump() if right.error else None,
    )
    changed = (
        left.kind != right.kind
        or left_name != right_name
        or bool(request_paths or response_paths or error_paths)
    )
    return {
        "left_seq": left.seq,
        "right_seq": right.seq,
        "kind_name_changed": left.kind != right.kind or left_name != right_name,
        "left_name": left_name,
        "right_name": right_name,
        "request_paths": request_paths,
        "response_paths": response_paths,
        "error_paths": error_paths,
        "changed": changed,
    }


def diff_v2_cassettes(left_path: str | Path, right_path: str | Path) -> dict[str, Any]:
    """Compare schema-v2 trajectories, detecting intermediate behavior changes."""
    from difflib import SequenceMatcher

    from agentrec.cassette.store import CassetteStore as V2CassetteStore
    from agentrec.cassette.store import CassetteStoreError
    from agentrec.validation import validate_v2_cassette

    for path in (left_path, right_path):
        result = validate_v2_cassette(path, level="structural")
        if not result["ok"]:
            raise CassetteStoreError("; ".join(result["errors"]))
    _, left = V2CassetteStore(left_path).load()
    _, right = V2CassetteStore(right_path).load()
    pairs: list[tuple[Any | None, Any | None]] = []
    if len(left) == len(right):
        pairs = list(zip(left, right, strict=True))
    else:
        matcher = SequenceMatcher(
            a=[_identity(item) for item in left],
            b=[_identity(item) for item in right],
            autojunk=False,
        )
        for tag, a0, a1, b0, b1 in matcher.get_opcodes():
            if tag == "equal":
                pairs.extend(zip(left[a0:a1], right[b0:b1], strict=True))
            elif tag == "delete":
                pairs.extend((item, None) for item in left[a0:a1])
            elif tag == "insert":
                pairs.extend((None, item) for item in right[b0:b1])
            else:
                old_segment = left[a0:a1]
                new_segment = right[b0:b1]
                common = min(len(old_segment), len(new_segment))
                pairs.extend(
                    zip(old_segment[:common], new_segment[:common], strict=True)
                )
                pairs.extend((item, None) for item in old_segment[common:])
                pairs.extend((None, item) for item in new_segment[common:])
    details: list[dict[str, Any]] = []
    added = removed = changed = 0
    for old, new in pairs:
        if old is None:
            assert new is not None
            added += 1
            details.append({"change": "added", "left_seq": None, "right_seq": new.seq})
        elif new is None:
            removed += 1
            details.append(
                {"change": "removed", "left_seq": old.seq, "right_seq": None}
            )
        else:
            detail = _step_diff(old, new)
            if detail["changed"]:
                changed += 1
                details.append({"change": "changed", **detail})
    return {
        "steps": max(len(left), len(right)),
        "left_steps": len(left),
        "right_steps": len(right),
        "added": added,
        "removed": removed,
        "changed": changed,
        "behavior_changed": bool(added or removed or changed),
        "duration_delta_ms": round(
            sum(item.duration_ms for item in right)
            - sum(item.duration_ms for item in left),
            3,
        ),
        "details": details,
    }
