"""Smoke tests for Recorder + JSONLStream."""
import json

from tape import Recorder, JSONLStream


def test_basic_session(tmp_path):
    p = tmp_path / "t.jsonl"
    with Recorder(p) as rec:
        rec.user_msg("hi")
        rec.assistant_msg("hello")

    events = list(JSONLStream(p))
    types = [e.type for e in events]
    assert types[0] == "session_start"
    assert types[-1] == "session_end"
    assert "user_msg" in types and "assistant_msg" in types


def test_tool_span_pairs(tmp_path):
    p = tmp_path / "t.jsonl"
    with Recorder(p) as rec:
        with rec.tool("add", {"a": 1, "b": 2}) as s:
            s.set_result(3)

    events = list(JSONLStream(p))
    starts = [e for e in events if e.type == "tool_call_start"]
    ends = [e for e in events if e.type == "tool_call_end"]
    assert len(starts) == 1 and len(ends) == 1
    assert ends[0].parent_id == starts[0].id
    assert ends[0].payload["result"] == 3


def test_exception_recorded(tmp_path):
    p = tmp_path / "t.jsonl"
    try:
        with Recorder(p) as rec:
            with rec.tool("boom", {}):
                raise ValueError("kaboom")
    except ValueError:
        pass
    events = list(JSONLStream(p))
    end = [e for e in events if e.type == "tool_call_end"][0]
    assert end.payload["ok"] is False
    assert "kaboom" in end.payload["error"]
