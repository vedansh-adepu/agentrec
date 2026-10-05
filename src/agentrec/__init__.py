"""agentrec: deterministic record-and-replay for AI-agent runs."""

__version__ = "0.1.0"


from .session import Session, session

__all__ = ["Session", "__version__", "session"]
