"""Error paths and nested trajectory differences protect externally visible behavior."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

import agentrec
from agentrec.cassette.store import CassetteStore, CassetteStoreError
from agentrec.cli import app
from agentrec.diff import _path_diffs, diff_v2_cassettes
from agentrec.pytest_plugin import agentrec_session
from agentrec.validation import validate_v2_cassette


def record(path, value):
    with agentrec.session(path, mode="once") as rec:

        @rec.tool
        def lookup() -> object:
            return value

        lookup()


def test_nested_list_diffs_report_add_remove_and_escape_paths(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    record(a, {"a/b": [1, 2], "remove": 1})
    record(b, {"a/b": [9], "add": 2})
    change = diff_v2_cassettes(a, b)
    paths = {d["path"] for d in change["details"][0]["response_paths"]}
    assert paths == {
        "/result/a~1b/0",
        "/result/a~1b/1",
        "/result/remove",
        "/result/add",
    }
    reverse = diff_v2_cassettes(b, a)
    assert reverse["changed"] == 1
    assert len(_path_diffs(list(range(20)), list(range(20, 40)))) == 10


@pytest.mark.parametrize("mode", ["all", "none", "once", "new_episodes"])
def test_regular_file_cannot_be_a_session(tmp_path: Path, mode: str) -> None:
    target = tmp_path / "file"
    target.write_text("keep", encoding="utf-8", newline="\n")
    with pytest.raises(CassetteStoreError):
        agentrec.session(target, mode=mode)
    assert target.read_text(encoding="utf-8") == "keep"
    assert not (tmp_path / ".file.agentrec.lock").exists()


def test_invalid_body_warning_threshold_fails_before_writer(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="positive"):
        agentrec.session(tmp_path / "no", max_body_bytes=0)
    assert list(tmp_path.iterdir()) == []


def test_unfinalized_cassette_cannot_replay(tmp_path: Path) -> None:
    path = tmp_path / "recording"
    record(path, 1)
    metadata, interactions = CassetteStore(path).load()
    recording = metadata.model_copy(
        update={"status": "recording", "finalized_at": None}
    )
    CassetteStore(path).save(recording, interactions, replace=True)
    assert not validate_v2_cassette(path)["ok"]
    with pytest.raises(CassetteStoreError, match="not finalized"):
        agentrec.session(path, mode="none")


def test_strict_order_is_not_swallowed_by_new_episodes(tmp_path: Path) -> None:
    path = tmp_path / "strict"
    with agentrec.session(path, mode="once") as rec:

        @rec.tool
        def lookup(value: int) -> int:
            return value

        lookup(1)
        lookup(2)
    with agentrec.session(path, mode="new_episodes", strict_order=True) as rec:

        @rec.tool
        def lookup(value: int) -> int:
            raise AssertionError("executed out of order")

        with pytest.raises(agentrec.ReplayOrderError):
            lookup(2)
        assert lookup(1) == 1 and lookup(2) == 2


@pytest.mark.parametrize("name", [None, "named", 1, "../escape"])
def test_pytest_fixture_mode_name_and_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name
) -> None:
    monkeypatch.delenv("AGENTREC_MODE", raising=False)
    monkeypatch.delenv("CI", raising=False)
    marker = None if name is None else SimpleNamespace(kwargs={"cassette": name})
    request = SimpleNamespace(
        node=SimpleNamespace(
            get_closest_marker=lambda _: marker, nodeid="test_fixture"
        ),
        config=SimpleNamespace(rootpath=tmp_path, getoption=lambda _: "once"),
    )
    iterator = agentrec_session.__wrapped__(request)
    if name == 1 or name == "../escape":
        with pytest.raises(ValueError):
            next(iterator)
        return
    rec = next(iterator)

    @rec.tool
    def lookup() -> int:
        return 1

    assert lookup() == 1
    with pytest.raises(StopIteration):
        next(iterator)
    assert (rec.path / "cassette.json").exists()
    assert not list((tmp_path / "tests/cassettes").glob("*.lock"))


def test_cli_help_debug_and_diff_text(tmp_path: Path) -> None:
    runner = CliRunner()
    assert runner.invoke(app, []).exit_code == 2
    debug = runner.invoke(app, ["--debug", "show", str(tmp_path / "missing")])
    assert debug.exit_code == 1 and isinstance(debug.exception, ValueError)
    a = tmp_path / "a"
    b = tmp_path / "b"
    record(a, [1])
    record(b, [2])
    changed = runner.invoke(app, ["diff", str(a), str(b), "--fail-on-change"])
    assert changed.exit_code == 1 and "/result/0" in changed.output
    stable = runner.invoke(app, ["diff", str(a), str(a)])
    assert stable.exit_code == 0 and "changed: 0" in stable.output
    validate = runner.invoke(app, ["validate", str(a), "--level", "structural"])
    assert validate.exit_code == 0
    request = tmp_path / "request.json"
    for payload in ([], {"kind": "unknown"}, {"kind": "tool"}):
        request.write_text(json.dumps(payload), encoding="utf-8", newline="\n")
        invalid = runner.invoke(app, ["inspect-miss", str(a), str(request)])
        assert invalid.exit_code == 2 and invalid.output.startswith("error:")


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("case", ["binary", "timeout", "gzip"])
def test_legacy_binary_gzip_and_transport_errors(
    tmp_path: Path, asynchronous: bool, case: str
) -> None:
    import gzip

    import httpx

    calls = 0
    path = tmp_path / "legacy"
    body = b"\xff\x00" if case == "binary" else b"decoded"

    def upstream(request):
        nonlocal calls
        calls += 1
        assert request.content == body
        if case == "timeout":
            raise httpx.ConnectTimeout("fake timeout", request=request)
        return httpx.Response(
            200,
            content=gzip.compress(body) if case == "gzip" else body,
            headers={"content-encoding": "gzip"} if case == "gzip" else {},
        )

    async def async_run(mode):
        async with (
            agentrec.session(path, mode=mode) as rec,
            httpx.AsyncClient(
                transport=agentrec.legacy_async_httpx_transport(
                    rec, httpx.MockTransport(upstream)
                )
            ) as client,
        ):
            if case == "timeout":
                with pytest.raises(httpx.ConnectTimeout):
                    await client.post("https://example.test", content=body)
            else:
                assert (
                    await client.post("https://example.test", content=body)
                ).content == body

    def sync_run(mode):
        with (
            agentrec.session(path, mode=mode) as rec,
            httpx.Client(
                transport=agentrec.legacy_httpx_transport(
                    rec, httpx.MockTransport(upstream)
                )
            ) as client,
        ):
            if case == "timeout":
                with pytest.raises(httpx.ConnectTimeout):
                    client.post("https://example.test", content=body)
            else:
                assert client.post("https://example.test", content=body).content == body

    for mode in ("once", "none"):
        asyncio.run(async_run(mode)) if asynchronous else sync_run(mode)
    assert calls == 1


def test_privacy_scans_lists_error_messages_and_secret_keys_without_leaking() -> None:
    from test_cassette_v2_store import sample_interaction, sample_metadata

    from agentrec.cassette.model import ErrorRecord
    from agentrec.redaction import Redactor, privacy_findings

    secret = "sk-FAKEFAKEFAKEFAKE"
    item = sample_interaction().model_copy(
        update={"response": {"result": [{secret: secret}]}}
    )
    metadata = sample_metadata([item]).model_copy(
        update={"error": ErrorRecord(type="ValueError", message=secret)}
    )
    findings = privacy_findings([item], metadata)
    assert len(findings) >= 3 and all(secret not in finding for finding in findings)
    redactor = Redactor(before_record_response=lambda value: dict(value, body=secret))
    assert "sk-FAKE" not in str(redactor.redact_response({}, kind="http"))
    assert redactor.redact_request({}, kind="http") == {}


def test_cli_http_inspection_and_explicit_privacy_flag(tmp_path: Path) -> None:
    import httpx2

    runner = CliRunner()
    path = tmp_path / "http"
    with (
        agentrec.session(path) as rec,
        httpx2.Client(
            transport=rec.transport(
                httpx2.MockTransport(
                    lambda request: httpx2.Response(200, content=b"ok")
                )
            )
        ) as client,
    ):
        client.get("https://example.test/")
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "kind": "http",
                "method": "GET",
                "url": "https://example.test/",
                "body": "",
                "headers": {},
            }
        ),
        encoding="utf-8",
        newline="\n",
    )
    assert runner.invoke(app, ["inspect-miss", str(path), str(request)]).exit_code == 0
    assert (
        runner.invoke(
            app, ["validate", str(path), "--level", "structural", "--privacy"]
        ).exit_code
        == 0
    )
    invalid = tmp_path / "invalid"
    invalid.mkdir()
    assert (
        runner.invoke(app, ["inspect-miss", str(invalid), str(request)]).exit_code == 2
    )


def test_diff_aligns_insert_delete_and_unequal_replacement(tmp_path: Path) -> None:
    def sequence(path, values):
        with agentrec.session(path) as rec:

            @rec.tool
            def lookup(value: int) -> int:
                return value

            for value in values:
                lookup(value)

    a = tmp_path / "a"
    b = tmp_path / "b"
    c = tmp_path / "c"
    sequence(a, [1, 2])
    sequence(b, [0, 1, 2])
    sequence(c, [4])
    assert diff_v2_cassettes(a, b)["added"] == 1
    assert diff_v2_cassettes(b, a)["removed"] == 1
    replacement = diff_v2_cassettes(a, c)
    assert replacement["changed"] == 1 and replacement["removed"] == 1
    reverse = diff_v2_cassettes(c, a)
    assert reverse["changed"] == 1 and reverse["added"] == 1


def test_canonical_unknown_storage_values_and_json_scalar_body_fail_clearly() -> None:
    from agentrec.canonical import (
        CanonicalValueError,
        decode_special_values,
        encode_special_values,
    )
    from agentrec.matching import MatchPolicy

    with pytest.raises(CanonicalValueError):
        encode_special_values(object())
    with pytest.raises(CanonicalValueError):
        decode_special_values(object())
    assert MatchPolicy()._body('"scalar"', "application/json") == {
        "kind": "json",
        "value": "scalar",
    }
