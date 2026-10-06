import inspect
import socket
from pathlib import Path

import pytest

from agentrec._legacy.core import AgentRecorder, AgentReplayer
from agentrec._legacy.hashing import hash_request
from agentrec._legacy.models import RunRecord
from agentrec._legacy.providers import FakeModelProvider, ModelRequest
from agentrec._legacy.store import CassetteStore
from agentrec._legacy.tools import default_tool_registry
from agentrec.errors import ReplayMissError


def make_model_request(content: str = "add 2 and 3") -> ModelRequest:
    return ModelRequest(
        model="fake-math",
        messages=[{"role": "user", "content": content}],
    )


def record_cassette(tmp_path: Path) -> tuple[CassetteStore, ModelRequest]:
    store = CassetteStore(tmp_path / "cassette")
    recorder = AgentRecorder(
        store=store,
        run=RunRecord(run_id="run_001", task="add 2 and 3"),
        provider=FakeModelProvider(),
        tools=default_tool_registry(),
    )
    request = make_model_request()
    recorder.record_model_call(request)
    recorder.record_tool_call("calculator", {"expression": "2+3"})
    recorder.finish("5")
    return store, request


def snapshot_files(path: Path) -> dict[Path, bytes]:
    return {
        file_path.relative_to(path): file_path.read_bytes()
        for file_path in sorted(path.rglob("*"))
        if file_path.is_file()
    }


def test_replayer_can_replay_recorded_model_call_from_cassette(
    tmp_path: Path,
) -> None:
    store, request = record_cassette(tmp_path)
    replayer = AgentReplayer(store)

    replayed = replayer.replay_model_call(request)

    assert replayed.output_text == "Use the calculator tool for: add 2 and 3"


def test_replayer_can_replay_recorded_tool_call_from_cassette(tmp_path: Path) -> None:
    store, _ = record_cassette(tmp_path)
    replayer = AgentReplayer(store)

    replayed = replayer.replay_tool_call("calculator", {"expression": "2+3"})

    assert replayed.name == "calculator"
    assert replayed.arguments == {"expression": "2+3"}
    assert replayed.output == {"result": 5}


def test_replayed_model_response_equals_recorded_response(tmp_path: Path) -> None:
    store = CassetteStore(tmp_path / "cassette")
    recorder = AgentRecorder(
        store=store,
        run=RunRecord(run_id="run_001", task="add 2 and 3"),
        provider=FakeModelProvider(),
        tools=default_tool_registry(),
    )
    request = make_model_request()
    recorded = recorder.record_model_call(request)

    replayed = AgentReplayer(store).replay_model_call(request)

    assert replayed == recorded


def test_replayed_tool_result_equals_recorded_result(tmp_path: Path) -> None:
    store = CassetteStore(tmp_path / "cassette")
    recorder = AgentRecorder(
        store=store,
        run=RunRecord(run_id="run_001", task="add 2 and 3"),
        provider=FakeModelProvider(),
        tools=default_tool_registry(),
    )
    recorded = recorder.record_tool_call("calculator", {"expression": "2+3"})

    replayed = AgentReplayer(store).replay_tool_call(
        "calculator",
        {"expression": "2+3"},
    )

    assert replayed == recorded


def test_replay_model_call_raises_replay_miss_for_changed_request(
    tmp_path: Path,
) -> None:
    store, _ = record_cassette(tmp_path)
    replayer = AgentReplayer(store)

    with pytest.raises(ReplayMissError):
        replayer.replay_model_call(make_model_request("add 2 and 4"))


def test_replay_tool_call_raises_replay_miss_for_changed_request(
    tmp_path: Path,
) -> None:
    store, _ = record_cassette(tmp_path)
    replayer = AgentReplayer(store)

    with pytest.raises(ReplayMissError):
        replayer.replay_tool_call("calculator", {"expression": "2+4"})


def test_replayer_does_not_accept_provider_or_tool_registry() -> None:
    signature = inspect.signature(AgentReplayer)

    assert list(signature.parameters) == ["store"]


def test_replayer_does_not_mutate_cassette_files_during_replay(tmp_path: Path) -> None:
    store, request = record_cassette(tmp_path)
    before = snapshot_files(store.path)
    replayer = AgentReplayer(store)

    replayer.replay_model_call(request)
    replayer.replay_tool_call("calculator", {"expression": "2+3"})
    replayer.read_final_output()

    assert snapshot_files(store.path) == before


def test_read_final_output_returns_recorded_final_output(tmp_path: Path) -> None:
    store, _ = record_cassette(tmp_path)

    assert AgentReplayer(store).read_final_output() == "5"


def test_replay_uses_hash_request_for_model_and_tool_hashes(tmp_path: Path) -> None:
    store, request = record_cassette(tmp_path)
    model_hash = hash_request(request.model_dump(mode="json"))
    tool_hash = hash_request(
        {"name": "calculator", "arguments": {"expression": "2+3"}},
    )

    replayer = AgentReplayer(store)

    assert store.read_interaction(model_hash, "model").response == (
        replayer.replay_model_call(request).model_dump(mode="json")
    )
    assert store.read_interaction(tool_hash, "tool").response == (
        replayer.replay_tool_call(
            "calculator",
            {"expression": "2+3"},
        ).model_dump(mode="json")
    )


def test_replayer_introduces_no_live_network_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, request = record_cassette(tmp_path)

    def fail_socket(*args: object, **kwargs: object) -> None:
        raise AssertionError("network should not be used")

    monkeypatch.setattr(socket, "socket", fail_socket)
    replayer = AgentReplayer(store)

    replayer.replay_model_call(request)
    replayer.replay_tool_call("calculator", {"expression": "2+3"})
    assert replayer.read_final_output() == "5"
