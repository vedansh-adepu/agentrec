"""Keep network blocking while providing Windows asyncio's local IPC pair."""

import socket
import sys

import pytest

# Captured before pytest-socket installs its per-test constructor guard.
_REAL_SOCKET = socket.socket


def _loopback_socketpair(family=None, type=socket.SOCK_STREAM, proto=0):
    family = socket.AF_INET if family is None else family
    if family not in (socket.AF_INET, socket.AF_INET6):
        raise ValueError("only IP loopback IPC is supported")
    if type != socket.SOCK_STREAM or proto != 0:
        raise ValueError("only TCP stream IPC is supported")
    host = "127.0.0.1" if family == socket.AF_INET else "::1"
    with _REAL_SOCKET(family, type, proto) as listener:
        listener.bind((host, 0))
        listener.listen(1)
        client = _REAL_SOCKET(family, type, proto)
        try:
            client.connect(listener.getsockname())
            # socket.accept() uses the globally guarded constructor. Wrap only
            # this accepted local IPC handle using the captured constructor.
            fd, _ = listener._accept()
            try:
                server = _REAL_SOCKET(family, type, proto, fileno=fd)
            except BaseException:
                socket.close(fd)
                raise
            return server, client
        except BaseException:
            client.close()
            raise


@pytest.fixture(autouse=True)
def windows_asyncio_ipc(monkeypatch):
    if sys.platform == "win32":
        monkeypatch.setattr(socket, "socketpair", _loopback_socketpair)
