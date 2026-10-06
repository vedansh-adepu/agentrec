import socket
from pathlib import Path

import pytest

from agentrec._legacy.core import AgentRecorder
from agentrec._legacy.hashing import hash_request
from agentrec._legacy.models import RunRecord
from agentrec._legacy.providers import FakeModelProvider, ModelRequest
from agentrec._legacy.store import CassetteStore
from agentrec._legacy.tools import default_tool_registry
from agentrec.errors import AgentRecError


def make_run() -> RunRecord:
    return RunRecord(run_id="run_001", task="add 2 and 3")


def make_model_request() -> ModelRequest:
    return ModelRequest(
        model="fake-math",
        messages=[{"role": "user", "content": "add 2 and 3"}],
    )


def make_recorder(tmp_path: Path) -> AgentRecorder:
    return AgentRecorder(
        store=CassetteStore(tmp_path / "cassette"),
        run=make_run(),
        provider=FakeModelProvider(),
        tools=default_tool_registry(),
    )


def test_recorder_initializes_cassette_folder(tmp_path: Path) -> None:
    make_recorder(tmp_path)

    cassette_path = tmp_path / "cassette"
    assert (cassette_path / "metadata.json").is_file()
    assert (cassette_path / "trace.jsonl").is_file()
    assert (cassette_path / "responses").is_dir()
    assert (cassette_path / "artifacts").is_dir()


def test_record_model_call_writes_interaction_step_and_returns_response(
    tmp_path: Path,
) -> None:
    recorder = make_recorder(tmp_path)
    request = make_model_request()

    response = recorder.record_model_call(request)

    request_dict = request.model_dump(mode="json")
    request_hash = hash_request(request_dict)
    interaction = recorder.store.read_interaction(request_hash, "model")
    steps = recorder.store.read_steps()

    assert response.output_text == "Use the calculator tool for: add 2 and 3"
    assert interaction.request_hash == request_hash
    assert interaction.kind == "model"
    assert interaction.request == request_dict
    assert interaction.response == response.model_dump(mode="json")
    assert interaction.usage == response.usage
    assert interaction.latency_ms is not None
    assert steps == recorder.run.steps
    assert len(steps) == 1
    assert steps[0].index == 0
    assert steps[0].kind == "model"
    assert steps[0].name == "fake-math"
    assert steps[0].request_hash == request_hash
    assert steps[0].input == request_dict
    assert steps[0].output == response.model_dump(mode="json")
    assert steps[0].usage == response.usage


def test_record_tool_call_writes_interaction_step_and_returns_tool_result(
    tmp_path: Path,
) -> None:
    recorder = make_recorder(tmp_path)
    arguments = {"expression": "2+3"}

    result = recorder.record_tool_call("calculator", arguments)

    request_dict = {"name": "calculator", "arguments": arguments}
    request_hash = hash_request(request_dict)
    interaction = recorder.store.read_interaction(request_hash, "tool")
    steps = recorder.store.read_steps()

    assert result.output == {"result": 5}
    assert interaction.request_hash == request_hash
    assert interaction.kind == "tool"
    assert interaction.request == request_dict
    assert interaction.response == result.model_dump(mode="json")
    assert interaction.usage is None
    assert interaction.latency_ms is not None
    assert steps == recorder.run.steps
    assert len(steps) == 1
    assert steps[0].index == 0
    assert steps[0].kind == "tool"
    assert steps[0].name == "calculator"
    assert steps[0].request_hash == request_hash
    assert steps[0].input == request_dict
    assert steps[0].output == result.model_dump(mode="json")


def test_model_and_tool_steps_preserve_order(tmp_path: Path) -> None:
    recorder = make_recorder(tmp_path)

    recorder.record_model_call(make_model_request())
    recorder.record_tool_call("calculator", {"expression": "2+3"})

    steps = recorder.store.read_steps()
    assert [step.index for step in steps] == [0, 1]
    assert [step.kind for step in steps] == ["model", "tool"]


def test_finish_writes_final_output_and_appends_final_step(tmp_path: Path) -> None:
    recorder = make_recorder(tmp_path)
    recorder.record_model_call(make_model_request())

    recorder.finish("5")

    steps = recorder.store.read_steps()
    assert recorder.store.read_final_output() == "5"
    assert [step.index for step in steps] == [0, 1]
    assert steps[-1].kind == "final"
    assert steps[-1].name == "final_output"
    assert steps[-1].request_hash is None
    assert steps[-1].input == {}
    assert steps[-1].output == {"content": "5"}


def test_finish_updates_metadata_final_output(tmp_path: Path) -> None:
    recorder = make_recorder(tmp_path)

    recorder.finish("5")

    metadata = recorder.store.read_metadata()
    assert metadata.final_output == "5"
    assert metadata.steps == recorder.store.read_steps()


def test_recorder_uses_hash_request_for_model_and_tool_hashes(tmp_path: Path) -> None:
    recorder = make_recorder(tmp_path)
    model_request = make_model_request()
    tool_arguments = {"expression": "2+3"}

    recorder.record_model_call(model_request)
    recorder.record_tool_call("calculator", tool_arguments)

    steps = recorder.store.read_steps()
    assert steps[0].request_hash == hash_request(model_request.model_dump(mode="json"))
    assert steps[1].request_hash == hash_request(
        {"name": "calculator", "arguments": tool_arguments},
    )


def test_unknown_tool_errors_are_not_silently_swallowed(tmp_path: Path) -> None:
    recorder = make_recorder(tmp_path)

    with pytest.raises(AgentRecError):
        recorder.record_tool_call("missing", {})

    assert recorder.store.read_steps() == []
    assert list((tmp_path / "cassette" / "responses").iterdir()) == []


def test_recorder_introduces_no_live_network_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_socket(*args: object, **kwargs: object) -> None:
        raise AssertionError("network should not be used")

    monkeypatch.setattr(socket, "socket", fail_socket)
    recorder = make_recorder(tmp_path)

    recorder.record_model_call(make_model_request())
    recorder.record_tool_call("calculator", {"expression": "2+3"})
    recorder.finish("5")

    assert recorder.store.read_final_output() == "5"
