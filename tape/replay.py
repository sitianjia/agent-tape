"""Replay tools from a tape.

The killer feature: during replay we don't actually call the original
tool function. We look up `(name, arguments)` in the recorded tape and
return the recorded result. That means you can:

  - rerun the agent's behavior offline, with no network
  - swap the model out and see how a different model would reason
    over the SAME tool outputs
  - regression-test prompt changes deterministically
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

from .recorder import Event
from .stream import JSONLStream


def _key(name: str, arguments: dict) -> str:
    # deterministic for any json-able args
    sig = json.dumps(arguments, sort_keys=True, ensure_ascii=False, default=str)
    return f"{name}::{hashlib.sha256(sig.encode()).hexdigest()[:16]}"


class Replay:
    """Build a lookup table of tool calls -> recorded results.

    Order of recorded calls for the same key is preserved; replay
    advances through them in order so repeated calls return their
    own original results.
    """

    def __init__(self, source: str | JSONLStream,
                 session_id: str | None = None) -> None:
        stream = source if isinstance(source, JSONLStream) else JSONLStream(source)
        # collect start+end events keyed by start id
        starts: dict[int, Event] = {}
        results: dict[str, list[Any]] = defaultdict(list)
        for ev in stream:
            if session_id and ev.session_id != session_id:
                continue
            if ev.type == "tool_call_start":
                starts[ev.id] = ev
            elif ev.type == "tool_call_end":
                start = starts.get(ev.parent_id) if ev.parent_id else None
                if not start:
                    continue
                k = _key(start.payload["name"], start.payload.get("arguments", {}))
                if ev.payload.get("ok", True):
                    results[k].append(ev.payload.get("result"))
                else:
                    results[k].append({"_error": ev.payload.get("error", "?")})
        self._results = results
        self._cursors: dict[str, int] = defaultdict(int)

    def call(self, name: str, arguments: dict | None = None) -> Any:
        """Look up the recorded result for this call. Raises if missing."""
        k = _key(name, arguments or {})
        if k not in self._results:
            raise KeyError(f"no recorded result for {name}({arguments!r})")
        c = self._cursors[k]
        if c >= len(self._results[k]):
            # rewind — caller may invoke the same tool more than recorded
            c = len(self._results[k]) - 1
        self._cursors[k] = c + 1
        out = self._results[k][c]
        if isinstance(out, dict) and "_error" in out:
            raise RuntimeError(f"recorded error: {out['_error']}")
        return out

    def reset(self) -> None:
        self._cursors.clear()

    def names(self) -> list[str]:
        return sorted({k.split("::")[0] for k in self._results})
