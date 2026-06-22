"""Pure, model-free tests for transcribe.py. No FunASR/torch/network needed.

transcribe.py only imports stdlib at module level (engine deps are imported lazily
inside each run_* function), so `import transcribe` works on a bare runner.
"""
import transcribe as T


# ---------- fmt_ts ----------
def test_fmt_ts_basic():
    assert T.fmt_ts(0) == "00:00"
    assert T.fmt_ts(5) == "00:05"
    assert T.fmt_ts(65) == "01:05"
    assert T.fmt_ts(600) == "10:00"


def test_fmt_ts_negative_clamps_to_zero():
    assert T.fmt_ts(-3) == "00:00"


# ---------- _whisper_lang ----------
def test_whisper_lang_defaults_to_zh():
    assert T._whisper_lang(None) == "zh"
    assert T._whisper_lang("") == "zh"


def test_whisper_lang_auto_means_none():
    assert T._whisper_lang("auto") is None


def test_whisper_lang_passthrough():
    assert T._whisper_lang("en") == "en"


# ---------- normalize_spk ----------
def test_normalize_spk_numbers_by_first_appearance():
    segs = [
        {"spk": "B", "text": "hi"},
        {"spk": "A", "text": "yo"},
        {"spk": "B", "text": "again"},
    ]
    out, n = T.normalize_spk(segs)
    assert n == 2
    assert [s["speaker"] for s in out] == ["Speaker 1", "Speaker 2", "Speaker 1"]


def test_normalize_spk_none_becomes_unknown_and_not_counted():
    segs = [{"spk": None, "text": "a"}, {"spk": None, "text": "b"}]
    out, n = T.normalize_spk(segs)
    assert n == 0
    assert all(s["speaker"] == "Speaker ?" for s in out)


# ---------- merge_adjacent ----------
def _seg(start, end, text, spk):
    return {"start": start, "end": end, "text": text, "speaker": spk}


def test_merge_joins_same_speaker_within_gap():
    segs = [_seg(0, 1, "hello", "Speaker 1"), _seg(1.5, 2.5, "world", "Speaker 1")]
    merged = T.merge_adjacent(segs)
    assert len(merged) == 1
    assert merged[0]["text"] == "hello world"
    assert merged[0]["end"] == 2.5


def test_merge_does_not_join_at_or_beyond_gap():
    segs = [_seg(0, 1, "a", "Speaker 1"), _seg(3.0, 4.0, "b", "Speaker 1")]
    assert len(T.merge_adjacent(segs)) == 2  # gap 2.0 == MERGE_GAP_SEC → no merge


def test_merge_does_not_join_different_speakers():
    segs = [_seg(0, 1, "a", "Speaker 1"), _seg(1.2, 2, "b", "Speaker 2")]
    assert len(T.merge_adjacent(segs)) == 2


def test_merge_negative_gap_not_merged_and_end_never_goes_backward():
    # overlapping / out-of-order segment: gap < 0 must NOT merge (avoids end-time corruption)
    segs = [_seg(0, 5, "a", "Speaker 1"), _seg(2, 3, "b", "Speaker 1")]
    merged = T.merge_adjacent(segs)
    assert len(merged) == 2
    assert merged[0]["end"] == 5


def test_merge_punctuation_aware_join():
    segs = [_seg(0, 1, "好。", "Speaker 1"), _seg(1.2, 2, "继续", "Speaker 1")]
    merged = T.merge_adjacent(segs)
    assert merged[0]["text"] == "好。继续"  # no extra space after terminal punctuation


def test_merge_never_collapses_unknown_speakers():
    # no-diarization engines label every chunk "Speaker ?"; merging would lose chunk timestamps
    segs = [_seg(0, 120, "a", "Speaker ?"), _seg(120, 240, "b", "Speaker ?")]
    merged = T.merge_adjacent(segs)
    assert len(merged) == 2
    assert [m["start"] for m in merged] == [0, 120]


# ---------- transcribe_with_fallback ----------
def test_fallback_advances_past_failing_engine(monkeypatch):
    calls = []

    def boom(wav, **kw):
        calls.append("boom")
        raise RuntimeError("model crashed")

    def good(wav, **kw):
        calls.append("good")
        return [{"start": 0, "end": 1, "text": "ok", "spk": None}]

    monkeypatch.setattr(T, "ENGINES", {"boom": boom, "good": good})
    monkeypatch.setattr(T, "wav_duration", lambda p: 0.0)
    eng, segs = T.transcribe_with_fallback("/nonexistent.wav", ["boom", "good"], diar=False)
    assert eng == "good"
    assert segs and segs[0]["text"] == "ok"
    assert calls == ["boom", "good"]


def test_fallback_treats_empty_result_as_failure(monkeypatch):
    monkeypatch.setattr(T, "ENGINES", {
        "empty": lambda wav, **kw: [],
        "good": lambda wav, **kw: [{"start": 0, "end": 1, "text": "x", "spk": None}],
    })
    monkeypatch.setattr(T, "wav_duration", lambda p: 0.0)
    eng, segs = T.transcribe_with_fallback("/x.wav", ["empty", "good"], diar=False)
    assert eng == "good"


def test_fallback_returns_none_when_all_fail(monkeypatch):
    def boom(wav, **kw):
        raise RuntimeError("x")

    monkeypatch.setattr(T, "ENGINES", {"a": boom, "b": boom})
    monkeypatch.setattr(T, "wav_duration", lambda p: 0.0)
    eng, segs = T.transcribe_with_fallback("/x.wav", ["a", "b"], diar=False)
    assert eng is None and segs == []


# ---------- engine_available ----------
def test_engine_available_cloud_requires_key_and_package(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert T.engine_available("openrouter") is False  # no key → unavailable even if requests installed
