"""Redact sensitive strings from tape payloads.

Stream a tape through this to produce a sanitized copy that's safe to
share or commit to a public bug report.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

from .stream import JSONLStream


def redact(in_path: str | Path, out_path: str | Path,
           patterns: Iterable[str] | None = None,
           replacement: str = "[REDACTED]") -> int:
    """Returns the number of redactions made."""
    pats = [re.compile(p) for p in (patterns or _DEFAULT_PATTERNS)]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w", encoding="utf-8") as f:
        for ev in JSONLStream(in_path):
            raw = json.dumps(ev.to_dict(), ensure_ascii=False)
            for p in pats:
                raw, k = p.subn(replacement, raw)
                n += k
            f.write(raw + "\n")
    return n


_DEFAULT_PATTERNS = [
    r"[\w._%+\-]+@[\w.\-]+\.[A-Za-z]{2,}",          # email
    r"\b1[3-9]\d{9}\b",                             # CN mobile
    r"sk-[A-Za-z0-9]{20,}",                         # api keys
    r"ghp_[A-Za-z0-9]{30,}",                        # github tokens
]
