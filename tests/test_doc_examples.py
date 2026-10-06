"""Execute marked documentation blocks and reject unclassified examples."""

import re
from pathlib import Path

import pytest

from examples.field_tech_agent.run import run_demo

ROOT = Path(__file__).parents[1]


def blocks(path: Path):
    text = path.read_text()
    return [
        (text[: match.start()], match.group(1), match.group(2))
        for match in re.finditer(r"```([^\n]*)\n(.*?)```", text, re.S)
    ]


@pytest.mark.parametrize("relative", ["README.md", "docs/index.md"])
def test_exact_quickstart_block_records_and_replays(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative: str
) -> None:
    monkeypatch.chdir(tmp_path)
    found = [
        (prefix, lang, body)
        for prefix, lang, body in blocks(ROOT / relative)
        if prefix.rstrip().endswith("<!-- tested: quickstart -->")
    ]
    assert len(found) == 1
    code = found[0][2]
    exec(compile(code, relative, "exec"), {})
    # Replace the upstream and tool body to prove the second execution replays.
    assert "lambda request:" in code
    assert 'return {"part": "IGN-9", "model": model}' in code
    replay = code.replace(
        "lambda request:",
        'lambda request: (_ for _ in ()).throw(AssertionError("upstream ran")) or',
    ).replace(
        'return {"part": "IGN-9", "model": model}',
        'raise AssertionError("replay executed tool")',
    )
    exec(compile(replay, relative, "exec"), {})


def test_readme_demo_output_is_captured_from_real_execution() -> None:
    output = [
        body
        for prefix, lang, body in blocks(ROOT / "README.md")
        if prefix.rstrip().endswith("<!-- tested: demo-output -->")
    ]
    assert output == ["\n".join(run_demo()) + "\n"]


def test_all_documentation_blocks_are_tested_or_explicitly_illustrative() -> None:
    paths = [
        ROOT / name
        for name in ("README.md", "CONTRIBUTING.md", "SECURITY.md", "CHANGELOG.md")
    ]
    paths += list((ROOT / "docs").rglob("*.md"))
    for path in paths:
        for prefix, _language, _body in blocks(path):
            assert (
                prefix.rstrip().endswith(
                    ("<!-- tested: quickstart -->", "<!-- tested: demo-output -->")
                )
                or "illustrative" in prefix.lower()
            ), str(path)
