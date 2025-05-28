"""Event recorder.

The whole design rests on one decision: every interesting moment in an
agent run is an Event with a typed payload, a monotonic id, and an
attached wall-clock timestamp. Everything else is wrapping around that.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Literal, Optional


EventType = Literal[
    "session_start", "session_end",
    "user_msg", "assistant_msg",
    "tool_call_start", "tool_call_end",
    "model_request", "model_response",
    "error", "note",
]


@dataclass
class Event:
    """One thing that happened. Has the boring fields you'd guess."""
    id: int
    session_id: str
    ts: float                                # unix seconds
    type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[int] = None
    elapsed_ms: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.parent_id is None:
            d.pop("parent_id")
        if self.elapsed_ms is None:
            d.pop("elapsed_ms")
        return d


class Recorder:
    """Thread-safe append-only event sink.

    Use as a context manager so session_start / session_end land
    correctly even on exception:

        with Recorder("tapes/run1.jsonl") as rec:
            rec.user_msg("hello")
            ...
    """

    def __init__(self, sink: str | os.PathLike, session_id: Optional[str] = None,
                 flush_every: int = 1) -> None:
        self.path = Path(sink)
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self._fp = None
        self._lock = threading.Lock()
        self._counter = 0
        self._flush_every = flush_every

    # --- lifecycle ---

    def __enter__(self) -> "Recorder":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fp = self.path.open("a", encoding="utf-8")
        self.emit("session_start", {"pid": os.getpid()})
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc:
            self.emit("error", {"type": exc_type.__name__ if exc_type else "?",
                                "msg": str(exc)})
        self.emit("session_end", {})
        self._fp.close()
        self._fp = None

    # --- low-level ---

    def emit(self, type_: EventType, payload: dict[str, Any],
             parent_id: Optional[int] = None,
             elapsed_ms: Optional[float] = None) -> int:
        if self._fp is None:
            raise RuntimeError("Recorder not active. Use as context manager.")
        with self._lock:
            self._counter += 1
            ev = Event(id=self._counter, session_id=self.session_id,
                       ts=time.time(), type=type_, payload=payload,
                       parent_id=parent_id, elapsed_ms=elapsed_ms)
            self._fp.write(json.dumps(ev.to_dict(), ensure_ascii=False) + "\n")
            if self._counter % self._flush_every == 0:
                self._fp.flush()
            return ev.id

    # --- convenience helpers ---

    def user_msg(self, content: str) -> int:
        return self.emit("user_msg", {"content": content})

    def assistant_msg(self, content: str, **extra) -> int:
        return self.emit("assistant_msg", {"content": content, **extra})

    def model_request(self, **kw) -> int:
        return self.emit("model_request", kw)

    def model_response(self, parent_id: int, elapsed_ms: float, **kw) -> int:
        return self.emit("model_response", kw,
                         parent_id=parent_id, elapsed_ms=elapsed_ms)

    def note(self, text: str) -> int:
        return self.emit("note", {"text": text})

    # context manager around a tool call: returns Span
    def tool(self, name: str, arguments: dict | None = None) -> "Span":
        return Span(self, name, arguments or {})


class Span:
    """Context manager that emits paired tool_call_start / tool_call_end."""

    def __init__(self, rec: Recorder, name: str, arguments: dict) -> None:
        self.rec = rec
        self.name = name
        self.arguments = arguments
        self._t0 = 0.0
        self.start_id = -1
        self.result: Any = None
        self.error: Optional[Exception] = None

    def __enter__(self) -> "Span":
        self._t0 = time.perf_counter()
        self.start_id = self.rec.emit(
            "tool_call_start",
            {"name": self.name, "arguments": self.arguments},
        )
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        elapsed = (time.perf_counter() - self._t0) * 1000
        payload = {"name": self.name, "ok": exc is None}
        if exc is not None:
            payload["error"] = f"{exc_type.__name__}: {exc}"
        else:
            payload["result"] = self.result
        self.rec.emit("tool_call_end", payload,
                      parent_id=self.start_id, elapsed_ms=elapsed)

    def set_result(self, value: Any) -> None:
        self.result = value
