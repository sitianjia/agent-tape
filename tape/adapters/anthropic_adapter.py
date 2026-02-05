"""Wrap an Anthropic client to record .messages.create calls."""
from __future__ import annotations

import time
from typing import Any

from ..recorder import Recorder


def wrap(client, rec: Recorder):
    orig = client.messages.create

    def patched(**kw: Any):
        req_id = rec.model_request(model=kw.get("model"),
                                   n_messages=len(kw.get("messages", [])))
        t0 = time.perf_counter()
        resp = orig(**kw)
        elapsed = (time.perf_counter() - t0) * 1000
        usage = getattr(resp, "usage", None)
        rec.model_response(
            req_id, elapsed_ms=elapsed,
            input_tokens=getattr(usage, "input_tokens", 0),
            output_tokens=getattr(usage, "output_tokens", 0),
            stop_reason=getattr(resp, "stop_reason", None),
        )
        return resp

    client.messages.create = patched
    return client
