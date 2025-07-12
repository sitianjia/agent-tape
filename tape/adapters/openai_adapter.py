"""Record every chat.completions.create call to a Recorder.

Usage:

    from openai import OpenAI
    from tape import Recorder
    from tape.adapters.openai_adapter import wrap

    client = wrap(OpenAI(), rec)
    client.chat.completions.create(...)   # now recorded
"""
from __future__ import annotations

import time
from typing import Any

from ..recorder import Recorder


def wrap(client, rec: Recorder):
    """Monkey-patch a client.chat.completions.create with recording."""
    orig = client.chat.completions.create

    def patched(**kw: Any):
        req_id = rec.model_request(model=kw.get("model"),
                                   n_messages=len(kw.get("messages", [])),
                                   has_tools=bool(kw.get("tools")))
        t0 = time.perf_counter()
        resp = orig(**kw)
        elapsed = (time.perf_counter() - t0) * 1000
        usage = getattr(resp, "usage", None)
        rec.model_response(
            req_id, elapsed_ms=elapsed,
            input_tokens=getattr(usage, "prompt_tokens", 0),
            output_tokens=getattr(usage, "completion_tokens", 0),
            finish_reason=getattr(resp.choices[0], "finish_reason", None),
        )
        return resp

    client.chat.completions.create = patched
    return client
