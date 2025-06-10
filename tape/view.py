"""Pretty-print a tape to the terminal."""
from __future__ import annotations

import textwrap
from datetime import datetime

from .stream import JSONLStream


_COLORS = {
    "session_start":  "\x1b[2m",
    "session_end":    "\x1b[2m",
    "user_msg":       "\x1b[36m",
    "assistant_msg":  "\x1b[33m",
    "tool_call_start":"\x1b[34m",
    "tool_call_end":  "\x1b[32m",
    "model_request":  "\x1b[2m",
    "model_response": "\x1b[2m",
    "error":          "\x1b[31m",
    "note":           "\x1b[35m",
}
_R = "\x1b[0m"


def render(path: str, session_id: str | None = None,
           width: int = 100, color: bool = True) -> str:
    lines = []
    for ev in JSONLStream(path):
        if session_id and ev.session_id != session_id:
            continue
        ts = datetime.fromtimestamp(ev.ts).strftime("%H:%M:%S")
        c = _COLORS.get(ev.type, "") if color else ""
        r = _R if color else ""
        if ev.type == "user_msg":
            body = ev.payload.get("content", "")
            lines.append(f"{c}{ts}  user:{r}")
            lines.append(textwrap.indent(textwrap.fill(body, width - 4), "    "))
        elif ev.type == "assistant_msg":
            body = ev.payload.get("content", "")
            lines.append(f"{c}{ts}  assistant:{r}")
            if body:
                lines.append(textwrap.indent(textwrap.fill(body, width - 4), "    "))
        elif ev.type == "tool_call_start":
            n = ev.payload.get("name", "?")
            args = ev.payload.get("arguments", {})
            lines.append(f"{c}{ts}  → {n}({args}){r}")
        elif ev.type == "tool_call_end":
            elapsed = ev.elapsed_ms or 0
            ok = ev.payload.get("ok", True)
            tag = "ok" if ok else "FAIL"
            note = ev.payload.get("error", "") if not ok \
                else str(ev.payload.get("result", ""))[:80]
            lines.append(f"{c}{ts}  ← {tag} {elapsed:.0f}ms  {note}{r}")
        elif ev.type == "note":
            lines.append(f"{c}{ts}  # {ev.payload.get('text','')}{r}")
        elif ev.type == "error":
            lines.append(f"{c}{ts}  !! {ev.payload}{r}")
    return "\n".join(lines)


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="View a tape file")
    ap.add_argument("path")
    ap.add_argument("--session", default=None)
    ap.add_argument("--no-color", action="store_true")
    a = ap.parse_args()
    print(render(a.path, session_id=a.session, color=not a.no_color))


if __name__ == "__main__":
    main()
