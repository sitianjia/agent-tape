import pytest

from tape import Recorder, Replay


def test_replay_basic(tmp_path):
    p = tmp_path / "r.jsonl"
    with Recorder(p) as rec:
        with rec.tool("get_price", {"fruit": "apple"}) as s:
            s.set_result(5.0)
        with rec.tool("get_price", {"fruit": "apple"}) as s:
            s.set_result(5.0)
        with rec.tool("get_price", {"fruit": "banana"}) as s:
            s.set_result(3.5)

    r = Replay(p)
    assert r.call("get_price", {"fruit": "apple"}) == 5.0
    assert r.call("get_price", {"fruit": "banana"}) == 3.5


def test_replay_missing_raises(tmp_path):
    p = tmp_path / "r.jsonl"
    with Recorder(p) as rec:
        with rec.tool("a", {}) as s:
            s.set_result(1)
    r = Replay(p)
    with pytest.raises(KeyError):
        r.call("b", {})


def test_replay_error_raises(tmp_path):
    p = tmp_path / "r.jsonl"
    try:
        with Recorder(p) as rec:
            with rec.tool("flaky", {}) as s:
                raise RuntimeError("nope")
    except RuntimeError:
        pass
    r = Replay(p)
    with pytest.raises(RuntimeError):
        r.call("flaky", {})
