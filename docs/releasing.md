# Releasing

Do not publish this development branch automatically. Before any release, review
all regression tests, the CI matrix, privacy limits, and the final wheel smoke test.
The package version comes only from src/agentrec/__init__.py via hatchling.

One-time setup: create the PyPI project and a Trusted Publisher for repository
vedansh-adepu/agentrec, workflow release.yml, environment pypi. Configure that
GitHub environment with a required reviewer. No stored PyPI API token is needed. Leave the repository variable
`PYPI_PUBLISH_ENABLED` unset until setup and review are complete; publishing
is guarded by it being exactly `true`.
Enable GitHub Pages using GitHub Actions before the Pages workflow is used.

The release workflow only publishes after its environment approval. It uses OIDC
Trusted Publishing and requests attestations. Tagging v1.0.0rc1 triggers the
workflow, so finish setup and require environment approval BEFORE creating/pushing
that tag. Do not treat a tag as a harmless preview. For a local dry-run, build a
wheel/sdist and install the wheel into a temporary venv without publishing.

The workflow and Pages deployment are prepared but were not triggered during
implementation. Verify repository/environment settings by hand before use.

VHS was not installed during implementation. To generate a real terminal GIF,
run `vhs docs/demo.tape` from the repository root with test dependencies installed.
The tape is committed, but no GIF is fabricated or embedded before generation.
