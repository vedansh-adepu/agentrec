from agentrec._legacy.hashing import hash_request


def test_same_request_gives_same_hash() -> None:
    request = {
        "model": "fake-math",
        "messages": [{"role": "user", "content": "add 2 and 3"}],
    }

    assert hash_request(request) == hash_request(request)


def test_dictionary_key_order_does_not_affect_hash() -> None:
    left = {
        "model": "fake-math",
        "messages": [{"role": "user", "content": "add 2 and 3"}],
        "temperature": 0,
    }
    right = {
        "temperature": 0,
        "messages": [{"content": "add 2 and 3", "role": "user"}],
        "model": "fake-math",
    }

    assert hash_request(left) == hash_request(right)


def test_meaningful_request_change_changes_hash() -> None:
    left = {
        "model": "fake-math",
        "messages": [{"role": "user", "content": "add 2 and 3"}],
    }
    right = {
        "model": "fake-math",
        "messages": [{"role": "user", "content": "add 2 and 4"}],
    }

    assert hash_request(left) != hash_request(right)


def test_meaningful_id_field_changes_hash() -> None:
    left = {"tool": "get_customer", "arguments": {"id": "customer_123"}}
    right = {"tool": "get_customer", "arguments": {"id": "customer_456"}}

    assert hash_request(left) != hash_request(right)


def test_unstable_fields_do_not_affect_hash() -> None:
    stable = {
        "model": "fake-math",
        "messages": [{"role": "user", "content": "add 2 and 3"}],
    }
    noisy = {
        "request_id": "req_123",
        "timestamp": "2026-06-02T10:00:00Z",
        "trace_id": "trace_abc",
        "model": "fake-math",
        "messages": [{"role": "user", "content": "add 2 and 3"}],
    }

    assert hash_request(stable) == hash_request(noisy)
