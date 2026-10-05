# agentrec

Deterministic record/replay for AI-agent runs: model calls and tool calls,
in order, offline.

Start with the [repository quickstart](https://github.com/vedansh-adepu/agentrec#quickstart)
and the offline field-tech demo. Read [architecture](architecture.md),
[matching](matching.md), and [cassette format](cassette-format.md) for guarantees.

<!-- tested: quickstart -->
```python
import httpx2
from openai import OpenAI
import agentrec

fake = httpx2.MockTransport(lambda request: httpx2.Response(200, json={
    "id": "chatcmpl-example", "object": "chat.completion", "created": 1,
    "model": "fake", "choices": [{"index": 0, "message": {
        "role": "assistant", "content": "Use IGN-9"}, "finish_reason": "stop"}]}))
with agentrec.session("quickstart", mode="once") as rec:
    @rec.tool
    def lookup_part(model: str) -> dict:
        return {"part": "IGN-9", "model": model}
    with OpenAI(api_key="test", http_client=httpx2.Client(transport=rec.transport(fake))) as client:
        answer = client.chat.completions.create(model="fake", messages=[{"role": "user", "content": "No heat"}])
        assert answer.choices[0].message.content == "Use IGN-9"
        assert lookup_part("F-100")["part"] == "IGN-9"
```
