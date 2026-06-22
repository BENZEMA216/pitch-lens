"""Pure tests for runlog.py helpers (no filesystem ledger writes)."""
import runlog as R


# ---------- _hhmmss ----------
def test_hhmmss_under_hour():
    assert R._hhmmss(0) == "00:00"
    assert R._hhmmss(65) == "01:05"
    assert R._hhmmss(599) == "09:59"


def test_hhmmss_at_and_over_hour():
    assert R._hhmmss(3600) == "1:00:00"
    assert R._hhmmss(3661) == "1:01:01"


def test_hhmmss_rounds():
    assert R._hhmmss(64.6) == "01:05"


# ---------- _parse_transcribe_log ----------
def test_parse_transcribe_log_full():
    txt = "=== 完成 ===  共 128 段 / 3 位说话人 / 总耗时 1234s（实际 RTF≈0.31）"
    secs, note = R._parse_transcribe_log(txt)
    assert secs == 1234.0
    assert "128段/3人" in note
    assert "RTF 0.31" in note


def test_parse_transcribe_log_partial():
    secs, note = R._parse_transcribe_log("总耗时 42s 没有别的")
    assert secs == 42.0
    assert note == ""  # no seg/rtf markers


def test_parse_transcribe_log_empty():
    secs, note = R._parse_transcribe_log("nothing relevant here")
    assert secs == 0.0
    assert note == ""
