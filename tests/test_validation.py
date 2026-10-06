import json
import socket
from pathlib import Path

from agentrec._legacy.examples import record_math_flow
from agentrec._legacy.validation import validate_cassette


def test_validate_cassette_returns_ok_for_valid_recorded_cassette(
    tmp_path: Path,
) -> None:
    run_path = tmp_path / "math_run"
    record_math_flow(run_path, "2+3")

    result = validate_cassette(run_path)

    assert result["ok"] is True
    assert result["errors"] == []


def test_validate_cassette_valid_summary_includes_expected_fields(
    tmp_path: Path,
) -> None:
    run_path = tmp_path / "math_run"
    record_math_flow(run_path, "2+3")

    result = validate_cassette(run_path)

    assert result["run_id"] == "math_flow"
    assert result["task"] == "Calculate 2+3"
    assert result["schema_version"] == "1"
    assert result["step_count"] == 3
    assert result["response_file_count"] == 2
    assert result["has_final_output"] is True


def test_validate_cassette_missing_path_returns_errors(tmp_path: Path) -> None:
    result = validate_cassette(tmp_path / "missing")

    assert result["ok"] is False
    assert any("Missing cassette path" in error for error in result["errors"])


def test_validate_cassette_missing_metadata_returns_error(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"
    record_math_flow(run_path, "2+3")
    (run_path / "metadata.json").unlink()

    result = validate_cassette(run_path)

    assert result["ok"] is False
    assert any("Missing metadata.json" in error for error in result["errors"])


def test_validate_cassette_malformed_metadata_returns_error(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"
    record_math_flow(run_path, "2+3")
    (run_path / "metadata.json").write_text("{", encoding="utf-8")

    result = validate_cassette(run_path)

    assert result["ok"] is False
    assert any("Invalid metadata.json" in error for error in result["errors"])


def test_validate_cassette_missing_schema_version_returns_error(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"
    record_math_flow(run_path, "2+3")
    metadata = json.loads((run_path / "metadata.json").read_text(encoding="utf-8"))
    metadata.pop("schema_version")
    (run_path / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    result = validate_cassette(run_path)

    assert result["ok"] is False
    assert any("Missing metadata schema_version" in error for error in result["errors"])


def test_validate_cassette_unsupported_schema_version_returns_error(
    tmp_path: Path,
) -> None:
    run_path = tmp_path / "math_run"
    record_math_flow(run_path, "2+3")
    metadata = json.loads((run_path / "metadata.json").read_text(encoding="utf-8"))
    metadata["schema_version"] = "999"
    (run_path / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    result = validate_cassette(run_path)

    assert result["ok"] is False
    assert any(
        "Unsupported metadata schema_version" in error for error in result["errors"]
    )


def test_validate_cassette_malformed_trace_returns_error(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"
    record_math_flow(run_path, "2+3")
    (run_path / "trace.jsonl").write_text("not json\n", encoding="utf-8")

    result = validate_cassette(run_path)

    assert result["ok"] is False
    assert any("Invalid trace.jsonl" in error for error in result["errors"])


def test_validate_cassette_out_of_order_trace_indexes_return_error(
    tmp_path: Path,
) -> None:
    run_path = tmp_path / "math_run"
    record_math_flow(run_path, "2+3")
    lines = (run_path / "trace.jsonl").read_text(encoding="utf-8").splitlines()
    first_step = json.loads(lines[0])
    first_step["index"] = 5
    lines[0] = json.dumps(first_step)
    (run_path / "trace.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = validate_cassette(run_path)

    assert result["ok"] is False
    assert any("step indexes must be ordered" in error for error in result["errors"])


def test_validate_cassette_malformed_response_json_returns_error(
    tmp_path: Path,
) -> None:
    run_path = tmp_path / "math_run"
    record_math_flow(run_path, "2+3")
    response_file = next((run_path / "responses").glob("*.json"))
    response_file.write_text("{", encoding="utf-8")

    result = validate_cassette(run_path)

    assert result["ok"] is False
    assert any("Invalid response file" in error for error in result["errors"])


def test_validate_cassette_response_filename_mismatch_returns_error(
    tmp_path: Path,
) -> None:
    run_path = tmp_path / "math_run"
    record_math_flow(run_path, "2+3")
    response_file = next((run_path / "responses").glob("*_tool.json"))
    renamed = response_file.with_name("wrong_tool.json")
    response_file.rename(renamed)

    result = validate_cassette(run_path)

    assert result["ok"] is False
    assert any("expected filename" in error for error in result["errors"])


def test_validate_cassette_is_read_only(tmp_path: Path) -> None:
    run_path = tmp_path / "math_run"
    record_math_flow(run_path, "2+3")
    before = _snapshot(run_path)

    validate_cassette(run_path)

    assert _snapshot(run_path) == before


def test_validate_cassette_uses_no_live_network_calls(
    tmp_path: Path,
    monkeypatch,
) -> None:
    run_path = tmp_path / "math_run"
    record_math_flow(run_path, "2+3")

    def fail_socket(*args: object, **kwargs: object) -> None:
        raise AssertionError("network should not be used")

    monkeypatch.setattr(socket, "socket", fail_socket)

    result = validate_cassette(run_path)

    assert result["ok"] is True


def _snapshot(path: Path) -> dict[str, bytes]:
    return {
        str(file_path.relative_to(path)): file_path.read_bytes()
        for file_path in sorted(path.rglob("*"))
        if file_path.is_file()
    }
