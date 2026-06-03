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
