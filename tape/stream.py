"""Reading tapes back."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterator

from .recorder import Event


class JSONLStream:
    """Iterate Events from a jsonl tape file."""

    def __init__(self, path: str | os.PathLike) -> None:
        self.path = Path(path)

    def __iter__(self) -> Iterator[Event]:
        import gzip
        opener = (gzip.open if str(self.path).endswith(".gz")
                  else open)
        with opener(self.path, "rt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                yield Event(
                    id=d["id"], session_id=d["session_id"], ts=d["ts"],
                    type=d["type"], payload=d.get("payload", {}),
                    parent_id=d.get("parent_id"),
                    elapsed_ms=d.get("elapsed_ms"),
                )

    def by_session(self) -> dict[str, list[Event]]:
        out: dict[str, list[Event]] = {}
        for ev in self:
            out.setdefault(ev.session_id, []).append(ev)
        return out
