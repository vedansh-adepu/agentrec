"""Strict Pydantic models for the agentrec cassette schema v2."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CASSETTE_MARKER: Literal["agentrec"] = "agentrec"
SCHEMA_VERSION: Literal[2] = 2


class StrictModel(BaseModel):
    """Reject unknown fields and implicit type coercion in cassette records."""

    model_config = ConfigDict(extra="forbid", strict=True)


class PolicyRecord(StrictModel):
    """Persist the exact matching policy identity and configuration."""

    name: str
    version: int = Field(ge=1)
    config: dict[str, Any]


class ErrorRecord(StrictModel):
    """Persist a failed call or session exception without an executable type."""

    type: str
    message: str


class CassetteMetadata(StrictModel):
    """Describe a schema-v2 cassette and bind it to its interaction file."""

    agentrec_cassette: Literal["agentrec"] = CASSETTE_MARKER
    schema_version: Literal[2] = SCHEMA_VERSION
    agentrec_version: str
    match_policy: PolicyRecord
    redaction_policy_version: int = Field(ge=1)
    status: Literal["complete", "failed", "recording"]
    created_at: datetime
    finalized_at: datetime | None
    interaction_count: int = Field(ge=0)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    error: ErrorRecord | None = None

    @model_validator(mode="after")
    def check_state(self) -> CassetteMetadata:
        """Require finalization metadata and a reason for failed runs."""
        if self.status == "recording" and self.finalized_at is not None:
            raise ValueError("recording cassette cannot have finalized_at")
        if self.status != "recording" and self.finalized_at is None:
            raise ValueError("finalized cassette requires finalized_at")
        if self.status == "failed" and self.error is None:
            raise ValueError("failed cassette requires error")
        return self


class Interaction(StrictModel):
    """Represent one ordered HTTP or tool boundary and its observed outcome."""

    seq: int = Field(ge=0)
    kind: Literal["http", "tool"]
    key: str = Field(pattern=r"^[0-9a-f]{64}$")
    occurrence: int = Field(ge=0)
    key_inputs_redacted: bool
    request: dict[str, Any]
    response: dict[str, Any] | None = None
    error: ErrorRecord | None = None
    started_at: datetime
    duration_ms: float = Field(ge=0)

    @model_validator(mode="after")
    def check_outcome(self) -> Interaction:
        """Require exactly one response or error for a finalized interaction."""
        if (self.response is None) == (self.error is None):
            raise ValueError("interaction requires exactly one response or error")
        return self
