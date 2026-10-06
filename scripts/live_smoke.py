"""Manual paid-provider verification; never invoked by CI."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}


def parse_args(
    argv: Sequence[str] | None = None, *, environ: Mapping[str, str] | None = None
):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openai-model")
    parser.add_argument("--anthropic-model")
    parser.add_argument("--max-tokens", type=int, default=32)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--allow-repo-path", action="store_true")
    args = parser.parse_args(argv)
    if args.max_tokens < 1:
        parser.error("--max-tokens must be positive")
    env = os.environ if environ is None else environ
    for provider, variable in PROVIDERS.items():
        if env.get(variable) and not getattr(args, f"{provider}_model"):
            parser.error(f"--{provider}-model is required when {variable} is set")
    return args


def guard_output(path: Path, *, allow_repo_path: bool = False) -> Path:
    resolved = path.expanduser().resolve()
    if resolved.is_relative_to(REPO_ROOT) and not allow_repo_path:
        raise ValueError("output inside repository requires --allow-repo-path")
    return resolved


def output_directory(args) -> Path:
    if args.output is not None:
        return guard_output(args.output, allow_repo_path=args.allow_repo_path)
    base = guard_output(Path(tempfile.gettempdir()))
    return Path(tempfile.mkdtemp(prefix="agentrec-live-smoke-", dir=base))


def provider_calls(provider: str, key: str, model: str, max_tokens: int, rec, upstream):
    import httpx2

    http = httpx2.Client(transport=rec.transport(upstream))
    messages = [{"role": "user", "content": "Reply with exactly OK."}]
    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=key, http_client=http, max_retries=0)
        create = client.chat.completions.create
        kwargs = {
            "model": model,
            "messages": messages,
            "max_completion_tokens": max_tokens,
        }
    else:
        from anthropic import Anthropic

        client = Anthropic(api_key=key, http_client=http, max_retries=0)
        create = client.messages.create
        kwargs = {"model": model, "messages": messages, "max_tokens": max_tokens}
    with client:
        response = create(**kwargs, stream=False).model_dump(mode="json")
        with create(**kwargs, stream=True) as stream:
            events = [event.model_dump(mode="json") for event in stream]
    return response, events


def verify_provider(
    provider: str, key: str, model: str, max_tokens: int, path: Path, *, upstream=None
):
    import httpx2

    import agentrec

    if path.exists():
        raise ValueError(
            "provider output already exists; choose a fresh output directory"
        )

    class CountingTransport(httpx2.BaseTransport):
        def __init__(self, inner=None):
            self.inner = inner
            self.calls = 0

        def handle_request(self, request):
            self.calls += 1
            if self.inner is None:
                raise AssertionError("replay reached upstream")
            return self.inner.handle_request(request)

        def close(self):
            if self.inner is not None:
                self.inner.close()

    recording = CountingTransport(
        httpx2.HTTPTransport() if upstream is None else upstream
    )
    with agentrec.session(path, mode="once") as rec:
        expected = provider_calls(provider, key, model, max_tokens, rec, recording)
    if recording.calls != 2:
        raise AssertionError("expected exactly two recording upstream calls")
    replay = CountingTransport()
    with agentrec.session(path, mode="none") as rec:
        actual = provider_calls(provider, key, model, max_tokens, rec, replay)
    if actual != expected or replay.calls != 0:
        raise AssertionError("parsed replay differs or contacted upstream")
    print(f"{provider}: parsed results identical; record calls=2; replay calls=0")
    for flags in (["--level", "replayable"], ["--privacy"]):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from agentrec.cli import app; app()",
                "validate",
                str(path),
                *flags,
                "--json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        print(f"{provider} validate {' '.join(flags)}: {result.stdout.strip()}")
        if result.returncode:
            raise RuntimeError("cassette CLI validation failed")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    active = []
    for provider, variable in PROVIDERS.items():
        key = os.environ.get(variable)
        if key:
            active.append((provider, key))
        else:
            print(f"{provider}: skipped ({variable} absent)")
    if not active:
        return 0
    try:
        output = output_directory(args)
        # Check every target before the first paid request.
        if any((output / provider).exists() for provider, _ in active):
            raise ValueError("provider output already exists")
        print(f"Output: {output}")
        for provider, key in active:
            verify_provider(
                provider,
                key,
                getattr(args, f"{provider}_model"),
                args.max_tokens,
                output / provider,
            )
    except Exception as exc:
        # SDK errors can contain credentials or request bodies; do not print them.
        print(
            f"Smoke verification failed ({type(exc).__name__}); inspect locally.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
