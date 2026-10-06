"""Catch unpinned actions and accidental workflow permission/trigger expansion."""

import re
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_all_workflows_pin_actions_and_declare_permissions() -> None:
    for path in (ROOT / ".github/workflows").glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        assert "permissions:" in text
        for action in re.findall(r"uses:\s*(\S+)", text):
            assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", action), (path, action)


def test_publishing_requires_opt_in_and_pages_only_follows_main() -> None:
    release = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    assert "if: vars.PYPI_PUBLISH_ENABLED == 'true'" in release
    assert 'tags: ["v*"]' in release and "name: pypi" in release
    assert "attestations: true" in release and "id-token: write" in release
    pages = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    assert "branches: [main]" in pages and "pull_request:" not in pages


def test_codeql_scans_pre_release_branch_before_pr() -> None:
    codeql = (ROOT / ".github/workflows/codeql.yml").read_text(encoding="utf-8")
    assert "  push:\n    branches: [main, v1-production]" in codeql
    assert "  pull_request:\n    branches: [main]" in codeql
