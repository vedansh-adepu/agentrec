# Offline tests and pytest plugin

The test suite uses `pytest-socket` with network sockets disabled. Local Unix
socketpairs remain available because asyncio needs them for its event loop.
All SDK integration tests use fake HTTP transports and no API credentials.

The optional `agentrec[pytest]` extra registers the `agentrec_session` fixture
and `@pytest.mark.agentrec(cassette="name")` marker. The fixture stores a
cassette under `tests/cassettes/`; without an explicit name it derives a safe,
stable name from the test node ID. Run with `--agentrec-mode=none` for sealed
replay, or `once`, `new_episodes`, and `all` when deliberately recording.

The mode precedence is the CLI option, then `AGENTREC_MODE`, then the default.
The default is `none` when `CI` is set and `once` otherwise. A replay miss
never reaches the fake or live upstream. Keep private cassettes out of Git and
review any cassette before committing it.
