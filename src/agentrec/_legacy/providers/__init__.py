"""Model provider interfaces and implementations."""

from agentrec._legacy.providers.base import ModelProvider, ModelRequest, ModelResponse
from agentrec._legacy.providers.fake import FakeModelProvider

__all__ = [
    "FakeModelProvider",
    "ModelProvider",
    "ModelRequest",
    "ModelResponse",
]
