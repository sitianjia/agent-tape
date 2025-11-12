"""Quick aggregate stats over one or more tapes."""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from .stream import JSONLStream


def summarize(path: str | Path) -> dict:
    n_sessions = set()
    tool_counts: Counter = Counter()
    tool_errors: Counter = Counter()
    tool_total_ms: defaultdict = defaultdict(float)
    total_input = 0
    total_output = 0

    for ev in JSONLStream(path):
        n_sessions.add(ev.session_id)
        if ev.type == "tool_call_start":
            tool_counts[ev.payload.get("name", "?")] += 1
        elif ev.type == "tool_call_end":
            name = ev.payload.get("name", "?")
            if not ev.payload.get("ok", True):
                tool_errors[name] += 1
            tool_total_ms[name] += ev.elapsed_ms or 0
        elif ev.type == "model_response":
            total_input += ev.payload.get("input_tokens", 0)
            total_output += ev.payload.get("output_tokens", 0)

    return {
        "sessions": len(n_sessions),
        "tool_calls": dict(tool_counts),
        "tool_errors": dict(tool_errors),
        "tool_avg_ms": {k: tool_total_ms[k] / max(tool_counts[k], 1)
                        for k in tool_counts},
        "tokens_in": total_input,
        "tokens_out": total_output,
    }
