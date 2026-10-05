"""Custom exceptions for agentrec."""


class AgentRecError(Exception):
    """Base error with a stable code, single-line message, and recovery hint."""

    code = "AR000"
    hint = "Check the input and the documented operation guarantees."

    def __init__(self, message: str) -> None:
        self.message = " ".join(message.splitlines())
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"{self.code} {self.message}\nhint: {self.hint}"


class CassetteError(AgentRecError):
    """Base exception for cassette storage errors."""

    code = "AR200"
    hint = "Check the cassette directory and its permissions."


class CassetteNotFoundError(CassetteError):
    """Raised when a requested cassette file or interaction is missing."""

    code = "AR201"
    hint = "Record the cassette before attempting replay."


class CassetteValidationError(CassetteError):
    """Raised when a cassette folder is malformed."""

    code = "AR202"
    hint = "Run agentrec validate and re-record damaged cassettes."


class ReplayMissError(AgentRecError):
    """Raised when replay mode cannot find a cached response."""

    code = "AR101"
    hint = "Compare the request and matching policy, or re-record the cassette."


class ReplayExhaustedError(ReplayMissError):
    """Raised when every recorded occurrence of a key has been consumed."""

    code = "AR102"
    hint = "Record enough occurrences for this run."


class ReplayOrderError(ReplayMissError):
    """Raised when strict global sequence order is violated."""

    code = "AR103"
    hint = "Restore recorded call order or disable strict_order."


class UnplayedInteractionsError(AgentRecError):
    """Raised when a replay session leaves recorded interactions unused."""

    code = "AR104"
    hint = "Consume all recorded interactions or set fail_on_unplayed=False."


class ReplayedToolError(AgentRecError):
    """Represent a recorded tool exception without executing the tool body."""

    code = "AR105"
    hint = "Inspect the recorded tool error; replay does not execute the tool."

    def __init__(self, original_type: str, original_message: str) -> None:
        self.original_type = original_type
        self.original_message = original_message
        super().__init__(f"{original_type}: {original_message}")


class ReplayedTransportError(AgentRecError):
    """Represent an unknown recorded HTTP transport exception."""

    code = "AR106"
    hint = "Inspect the recorded error or re-record with a supported transport."
