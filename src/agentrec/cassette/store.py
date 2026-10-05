"""Validated schema-v2 cassette I/O with atomic files and one writer."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

from pydantic import ValidationError

from agentrec.errors import AgentRecError

from .model import (
    SCHEMA_VERSION,
    CassetteMetadata,
    Interaction,
)

KEY_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class CassetteStoreError(AgentRecError):
    """Base error for invalid, unsafe, or unavailable cassettes."""

    code = "AR203"
    hint = "Check cassette ownership, format, and filesystem permissions."


class CassetteVersionError(CassetteStoreError):
    """An existing cassette uses a schema this release cannot read."""

    code = "AR204"
    hint = "Re-record using schema v2; see docs/migration.md."


class CassetteOwnershipError(CassetteStoreError):
    """A destructive operation targeted a directory agentrec does not own."""

    code = "AR205"
    hint = "Choose a new directory or a valid owned cassette."


class CassetteLockedError(CassetteStoreError):
    """Another writer already holds the cassette path lock."""

    code = "AR206"
    hint = "Wait for the active writer; inspect stale locks after a crash."


def _atomic_write(path: Path, data: bytes) -> None:
    """Replace one file after flush/fsync, then best-effort sync its directory."""
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.replace(temporary, path)
        except PermissionError:
            os.replace(temporary, path)
        if os.name != "nt":
            try:
                directory_fd = os.open(path.parent, os.O_RDONLY)
            except OSError:
                return
            try:
                os.fsync(directory_fd)
            except OSError:
                pass
            finally:
                os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)


class CassetteStore:
    """Read and atomically finalize an owned two-file schema-v2 cassette."""

    def __init__(self, path: str | Path) -> None:
        """Bind to a directory without following a symlink at its final component."""
        self.path = Path(path)
        if self.path.is_symlink():
            raise CassetteStoreError("cassette path must not be a symlink")

    def _file(self, name: str) -> Path:
        """Resolve a fixed cassette filename and prove it stays within the folder."""
        if name not in {"cassette.json", "interactions.jsonl"}:
            raise CassetteStoreError("unexpected cassette filename")
        base = self.path.resolve()
        candidate = self.path / name
        if candidate.is_symlink() or candidate.resolve().parent != base:
            raise CassetteStoreError("cassette file escapes its directory")
        return candidate

    def path_for_key(self, key: str) -> Path:
        """Validate a public hash input before returning a contained path."""
        if not KEY_PATTERN.fullmatch(key):
            raise CassetteStoreError("key must be a lowercase SHA-256 hex digest")
        candidate = self.path / key
        if candidate.resolve().parent != self.path.resolve():
            raise CassetteStoreError("key path escapes cassette directory")
        return candidate

    def owns(self) -> bool:
        """Return whether the path contains valid schema-v2 ownership metadata."""
        try:
            CassetteMetadata.model_validate_json(
                self._file("cassette.json").read_bytes()
            )
        except (OSError, ValueError, CassetteStoreError):
            return False
        return True

    def require_owned(self) -> None:
        """Refuse destructive access to unmarked or symlinked directories."""
        if self.path.is_symlink() or not self.owns():
            raise CassetteOwnershipError("directory is not an owned agentrec cassette")

    @contextmanager
    def writer_lock(self) -> Iterator[None]:
        """Hold an exclusive advisory lock for this cassette path."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.path.parent / f".{self.path.name}.agentrec.lock"
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise CassetteLockedError(
                f"cassette writer is already active: {self.path}"
            ) from exc
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(str(os.getpid()))
                stream.flush()
                os.fsync(stream.fileno())
            yield
        finally:
            lock.unlink(missing_ok=True)

    def save(
        self,
        metadata: CassetteMetadata,
        interactions: Sequence[Interaction],
        *,
        replace: bool = False,
    ) -> None:
        """Finalize two files, writing interactions first and metadata last."""
        if self.path.is_symlink():
            raise CassetteStoreError("cassette path must not be a symlink")
        if self.path.exists():
            if not self.path.is_dir():
                raise CassetteStoreError("cassette path is not a directory")
            if self.owns():
                if not replace:
                    raise CassetteOwnershipError(
                        "cassette already exists; replacement is not allowed"
                    )
            elif any(self.path.iterdir()):
                raise CassetteOwnershipError("refusing to replace an unowned directory")
        if metadata.schema_version != SCHEMA_VERSION:
            raise CassetteVersionError("only schema v2 can be written")
        if metadata.interaction_count != len(interactions):
            raise CassetteStoreError("metadata interaction count does not match")
        if [item.seq for item in interactions] != list(range(len(interactions))):
            raise CassetteStoreError("interaction sequence must be contiguous")
        data = b"".join(
            json.dumps(
                item.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
            for item in interactions
        )
        digest = hashlib.sha256(data).hexdigest()
        if metadata.content_sha256 != digest:
            raise CassetteStoreError(
                "metadata content hash does not match interactions"
            )
        with self.writer_lock():
            if self.path.is_symlink():
                raise CassetteStoreError("cassette path must not be a symlink")
            if self.path.exists() and any(self.path.iterdir()):
                if not self.owns():
                    raise CassetteOwnershipError(
                        "refusing to replace an unowned directory"
                    )
                if not replace:
                    raise CassetteOwnershipError(
                        "cassette already exists; replacement is not allowed"
                    )
            self.path.mkdir(parents=True, exist_ok=True)
            _atomic_write(self._file("interactions.jsonl"), data)
            _atomic_write(
                self._file("cassette.json"),
                json.dumps(
                    metadata.model_dump(mode="json"),
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")
                + b"\n",
            )

    def load(self) -> tuple[CassetteMetadata, list[Interaction]]:
        """Load schema v2, rejecting unsupported versions and invalid records."""
        if (
            not self._file("cassette.json").exists()
            and (self.path / "metadata.json").exists()
        ):
            raise CassetteVersionError(
                "schema v1 is not supported by agentrec 1.x; "
                "re-record (see docs/migration.md)"
            )
        try:
            metadata_bytes = self._file("cassette.json").read_bytes()
            raw = json.loads(metadata_bytes)
        except (OSError, ValueError) as exc:
            raise CassetteStoreError("missing or invalid cassette.json") from exc
        if not isinstance(raw, dict):
            raise CassetteStoreError("cassette.json must be an object")
        version = raw.get("schema_version")
        if version != SCHEMA_VERSION:
            if version == 1 or (self.path / "metadata.json").exists():
                raise CassetteVersionError(
                    "schema v1 is not supported by agentrec 1.x; "
                    "re-record (see docs/migration.md)"
                )
            raise CassetteVersionError(
                f"unsupported cassette schema version: {version!r}"
            )
        try:
            metadata = CassetteMetadata.model_validate_json(metadata_bytes)
            lines = (
                self._file("interactions.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            )
            interactions = [Interaction.model_validate_json(line) for line in lines]
        except (OSError, ValueError, ValidationError) as exc:
            raise CassetteStoreError("invalid schema-v2 cassette contents") from exc
        return metadata, interactions
