from agentrec._legacy.models import (
    CASSETTE_SCHEMA_VERSION,
    CachedInteraction,
    RunRecord,
    Step,
    Usage,
)


def test_run_record_serializes_to_json() -> None:
    run = RunRecord(
        run_id="run_001",
        task="add 2 and 3",
        steps=[
            Step(
                index=0,
                kind="model",
                name="fake-math",
                request_hash="abc123",
                input={"messages": [{"role": "user", "content": "add 2 and 3"}]},
                output={"content": "use calculator"},
                usage=Usage(input_tokens=5, output_tokens=3, total_tokens=8),
            ),
            Step(
                index=1,
                kind="final",
                name="final_output",
                output={"content": "5"},
            ),
        ],
        final_output="5",
    )

    payload = run.model_dump_json()

    assert '"run_id":"run_001"' in payload
    assert f'"schema_version":"{CASSETTE_SCHEMA_VERSION}"' in payload
    assert '"final_output":"5"' in payload


def test_cached_interaction_round_trips_through_json() -> None:
    interaction = CachedInteraction(
        request_hash="abc123",
        kind="tool",
        request={"name": "calculator", "arguments": {"expression": "2+3"}},
        response={"result": 5},
        latency_ms=1.5,
    )

    payload = interaction.model_dump_json()
    restored = CachedInteraction.model_validate_json(payload)

    assert restored == interaction
