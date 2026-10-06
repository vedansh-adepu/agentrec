"""Manual smoke parsing and filesystem guards; no credentials or live calls."""

import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "live_smoke", Path(__file__).resolve().parents[1] / "scripts/live_smoke.py"
)
assert SPEC and SPEC.loader
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


def test_models_required_only_for_active_providers():
    args = smoke.parse_args([], environ={})
    assert args.openai_model is None and args.anthropic_model is None
    for provider, variable in smoke.PROVIDERS.items():
        with pytest.raises(SystemExit) as error:
            smoke.parse_args([], environ={variable: "fake-key"})
        assert error.value.code == 2
        args = smoke.parse_args(
            [f"--{provider}-model", "fake-model"], environ={variable: "fake-key"}
        )
        assert getattr(args, f"{provider}_model") == "fake-model"
    with pytest.raises(SystemExit):
        smoke.parse_args(["--max-tokens", "0"], environ={})


def test_output_guard_before_creation(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(smoke, "REPO_ROOT", repo)
    inside = repo / "nested" / "run"
    args = smoke.parse_args(["--output", str(inside)], environ={})
    with pytest.raises(ValueError, match="--allow-repo-path"):
        smoke.output_directory(args)
    assert not inside.parent.exists()
    assert smoke.guard_output(inside, allow_repo_path=True) == inside
    assert smoke.guard_output(repo / ".." / "outside") == tmp_path / "outside"
    with pytest.raises(ValueError):
        smoke.guard_output(repo / "outside" / ".." / "run")


def test_default_output_outside_repo_and_unsafe_temp_base_refused(
    tmp_path, monkeypatch
):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(smoke, "REPO_ROOT", repo)
    monkeypatch.setattr(smoke.tempfile, "gettempdir", lambda: str(tmp_path))
    args = smoke.parse_args([], environ={})
    output = smoke.output_directory(args)
    assert output.parent == tmp_path and output.name.startswith("agentrec-live-smoke-")
    monkeypatch.setattr(smoke.tempfile, "gettempdir", lambda: str(repo))
    with pytest.raises(ValueError):
        smoke.output_directory(args)
    assert not list(repo.iterdir())


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_complete_smoke_with_fake_sdk_http_and_real_cli(tmp_path, provider, capsys):
    import json

    import httpx2
    from test_session_httpx2 import chat_response

    calls = []

    def upstream(request):
        body = json.loads(request.content)
        calls.append(body)
        if body["stream"]:
            if provider == "openai":
                event = {
                    "id": "chatcmpl-fake",
                    "object": "chat.completion.chunk",
                    "created": 1,
                    "model": "fake-model",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": "OK"},
                            "finish_reason": "stop",
                        }
                    ],
                }
                data = "data: " + json.dumps(event) + "\n\ndata: [DONE]\n\n"
            else:
                data = 'event: message_stop\ndata: {"type":"message_stop"}\n\n'
            return httpx2.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=data.encode(),
            )
        response = (
            chat_response("OK")
            if provider == "openai"
            else {
                "id": "msg_fake",
                "type": "message",
                "role": "assistant",
                "model": "fake-model",
                "content": [{"type": "text", "text": "OK"}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 1, "output_tokens": 1},
            }
        )
        return httpx2.Response(200, json=response)

    smoke.verify_provider(
        provider,
        "fake-key",
        "fake-model",
        32,
        tmp_path / provider,
        upstream=httpx2.MockTransport(upstream),
    )
    assert len(calls) == 2 and [call["stream"] for call in calls] == [False, True]
    output = capsys.readouterr().out
    assert "replay calls=0" in output and output.count('"ok": true') == 2
    assert "fake-key" not in output
