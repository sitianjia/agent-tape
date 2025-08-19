from tape import Recorder
from tape.redact import redact


def test_default_patterns_remove_email_and_keys(tmp_path):
    src = tmp_path / "raw.jsonl"
    dst = tmp_path / "clean.jsonl"
    with Recorder(src) as rec:
        rec.user_msg("contact me at alice@example.com or 13800000000")
        rec.note("internal key: sk-abcdefghij0123456789ABCD")

    n = redact(src, dst)
    body = dst.read_text()
    assert n > 0
    assert "alice@example.com" not in body
    assert "13800000000" not in body
    assert "sk-abcdefghij" not in body
