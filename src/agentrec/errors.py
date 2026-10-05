"""Custom exceptions for agentrec."""


class AgentRecError(Exception):
    """Base exception for all agentrec errors."""


class CassetteError(AgentRecError):
    """Base exception for cassette storage errors."""


class CassetteNotFoundError(CassetteError):
    """Raised when a requested cassette file or interaction is missing."""


class CassetteValidationError(CassetteError):
    """Raised when a cassette folder is malformed."""


class ReplayMissError(AgentRecError):
    """Raised when replay mode cannot find a cached response."""


class ReplayExhaustedError(ReplayMissError):
    """Raised when every recorded occurrence of a key has been consumed."""


class ReplayOrderError(ReplayMissError):
    """Raised when strict global sequence order is violated."""


class UnplayedInteractionsError(AgentRecError):
    """Raised when a replay session leaves recorded interactions unused."""


class ReplayedToolError(AgentRecError):
    """Represent a recorded tool exception without executing the tool body."""

    def __init__(self, original_type: str, original_message: str) -> None:
        self.original_type = original_type
        self.original_message = original_message
        super().__init__(f"{original_type}: {original_message}")


class ReplayedTransportError(AgentRecError):
    """Represent an unknown recorded HTTP transport exception."""
