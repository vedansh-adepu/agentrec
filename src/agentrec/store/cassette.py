"""Local filesystem cassette store."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from agentrec.errors import CassetteNotFoundError, CassetteValidationError
from agentrec.models import CachedInteraction, RunRecord, Step


class CassetteStore:
    """Read and write cassette data in a local folder."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.responses_path = self.path / "responses"
        self.artifacts_path = self.path / "artifacts"
        self.metadata_path = self.path / "metadata.json"
        self.trace_path = self.path / "trace.jsonl"
        self.final_output_path = self.artifacts_path / "final_output.txt"

    def initialize(self, run: RunRecord) -> None:
        """Create the cassette folder structure and write metadata."""

        self.path.mkdir(parents=True, exist_ok=True)
        self.responses_path.mkdir(exist_ok=True)
        self.artifacts_path.mkdir(exist_ok=True)
        self.write_metadata(run)
        self.trace_path.touch(exist_ok=True)

    def write_metadata(self, run: RunRecord) -> None:
        """Write cassette run metadata."""

        self.path.mkdir(parents=True, exist_ok=True)
        self.metadata_path.write_text(run.model_dump_json(), encoding="utf-8")

    def read_metadata(self) -> RunRecord:
        """Read cassette run metadata."""

        if not self.metadata_path.exists():
            raise CassetteNotFoundError(f"Missing cassette metadata: {self.metadata_path}")
        return RunRecord.model_validate_json(
            self.metadata_path.read_text(encoding="utf-8"),
        )

    def append_step(self, step: Step) -> None:
        """Append one trace step as a JSON line."""

        self.path.mkdir(parents=True, exist_ok=True)
        with self.trace_path.open("a", encoding="utf-8") as trace_file:
            trace_file.write(step.model_dump_json())
            trace_file.write("\n")

    def read_steps(self) -> list[Step]:
        """Read trace steps in recorded order."""

        if not self.trace_path.exists():
            raise CassetteNotFoundError(f"Missing cassette trace: {self.trace_path}")

        steps: list[Step] = []
        for line in self.trace_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                steps.append(Step.model_validate_json(line))
        return steps

    def write_interaction(self, interaction: CachedInteraction) -> Path:
        """Write one cached model or tool interaction."""

        self.responses_path.mkdir(parents=True, exist_ok=True)
        path = self._interaction_path(interaction.request_hash, interaction.kind)
        path.write_text(interaction.model_dump_json(), encoding="utf-8")
        return path

    def read_interaction(
        self,
        request_hash: str,
        kind: Literal["model", "tool"],
    ) -> CachedInteraction:
        """Read one cached model or tool interaction by request hash."""

        path = self._interaction_path(request_hash, kind)
        if not path.exists():
            raise CassetteNotFoundError(f"Missing cached interaction: {path}")
        return CachedInteraction.model_validate_json(path.read_text(encoding="utf-8"))

    def write_final_output(self, text: str) -> Path:
        """Write the final agent output artifact."""

        self.artifacts_path.mkdir(parents=True, exist_ok=True)
        self.final_output_path.write_text(text, encoding="utf-8")
        return self.final_output_path

    def read_final_output(self) -> str:
        """Read the final agent output artifact."""

        if not self.final_output_path.exists():
            raise CassetteNotFoundError(
                f"Missing final output artifact: {self.final_output_path}",
            )
        return self.final_output_path.read_text(encoding="utf-8")

    def validate(self) -> None:
        """Validate the required cassette folder structure."""

        if not self.metadata_path.is_file():
            raise CassetteValidationError(f"Missing metadata.json: {self.metadata_path}")
        if not self.responses_path.is_dir():
            raise CassetteValidationError(f"Missing responses directory: {self.responses_path}")
        if not self.artifacts_path.is_dir():
            raise CassetteValidationError(f"Missing artifacts directory: {self.artifacts_path}")

    def _interaction_path(self, request_hash: str, kind: Literal["model", "tool"]) -> Path:
        return self.responses_path / f"{request_hash}_{kind}.json"
