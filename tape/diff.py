"""Compare two tapes — list semantic differences in tool-call sequence."""
from __future__ import annotations

from .stream import JSONLStream


def _tool_sequence(path: str) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    for ev in JSONLStream(path):
        if ev.type == "tool_call_start":
            out.append((ev.payload.get("name", "?"),
                        ev.payload.get("arguments", {})))
    return out


def diff_tools(a: str, b: str) -> list[str]:
    sa, sb = _tool_sequence(a), _tool_sequence(b)
    out: list[str] = []
    n = max(len(sa), len(sb))
    for i in range(n):
        if i >= len(sa):
            out.append(f"+ step {i}: {sb[i][0]}({sb[i][1]})")
        elif i >= len(sb):
            out.append(f"- step {i}: {sa[i][0]}({sa[i][1]})")
        elif sa[i] != sb[i]:
            out.append(f"~ step {i}: {sa[i][0]}({sa[i][1]}) -> {sb[i][0]}({sb[i][1]})")
        else:
            out.append(f"= step {i}: {sa[i][0]}({sa[i][1]})")
    return out
