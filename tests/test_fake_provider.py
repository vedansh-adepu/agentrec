import socket

import pytest

from agentrec.providers import FakeModelProvider, ModelRequest


def make_request(content: str = "add 2 and 3") -> ModelRequest:
    return ModelRequest(
        model="fake-math",
        messages=[{"role": "user", "content": content}],
    )


def test_fake_provider_returns_deterministic_output_for_same_request() -> None:
    provider = FakeModelProvider()
    request = make_request()

    assert provider.complete(request) == provider.complete(request)


def test_fake_provider_uses_response_map_when_provided() -> None:
    provider = FakeModelProvider(response_map={"add 2 and 3": "Mapped response"})

    response = provider.complete(make_request())

    assert response.output_text == "Mapped response"


def test_fake_provider_includes_usage_information() -> None:
    provider = FakeModelProvider()

    response = provider.complete(make_request())

    assert response.usage is not None
    assert response.usage.input_tokens > 0
    assert response.usage.output_tokens > 0
    assert response.usage.total_tokens == (
        response.usage.input_tokens + response.usage.output_tokens
    )


def test_fake_provider_makes_no_network_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_socket(*args: object, **kwargs: object) -> None:
        raise AssertionError("network should not be used")

    monkeypatch.setattr(socket, "socket", fail_socket)

    response = FakeModelProvider().complete(make_request())

    assert response.output_text == "Use the calculator tool for: add 2 and 3"
