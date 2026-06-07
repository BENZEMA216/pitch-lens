#!/usr/bin/env python3
"""
transcribe.py — 把会议/对谈录音/视频（投资人/FA/客户/团队/访谈…）转成「带时间戳 + 说话人标签」的对话稿。

本地优先，API 兜底。引擎选择顺序（--engine auto）：
  funasr   本地，中文最强，含 VAD+标点+说话人分离(cam++)   ← 默认首选
  mlx      本地 mlx-whisper（Apple Silicon），多语强，无说话人
  groq     Groq Whisper-large-v3（API，需 GROQ_API_KEY），快，无说话人→可选 pyannote
  dashscope 阿里 SenseVoice（API，需 DASHSCOPE_API_KEY），中文优化便宜

用法:
  python3 transcribe.py 录音.m4a
  python3 transcribe.py 录音.mp4 --out 录音.transcript.md --engine funasr
  python3 transcribe.py 录音.wav --engine groq            # 走 API
  python3 transcribe.py 录音.m4a --no-diar                # 跳过说话人分离

输出: <name>.transcript.md（人读） + <name>.transcript.json（机读，毫秒时间戳+spk）
     + <name>.transcript.log（结构化日志：每阶段耗时、ETA、心跳）  ← v2 日志机制

日志（解决"卡在结构化看不到进度"）：
- 启动即打印音频时长 + 预计耗时(ETA, 本机 RTF≈0.35)。
- 每个阶段(转码/模型加载/转录+分离/合成写出)单独计时。
- 转录是单次阻塞调用 → 起一个**心跳线程**，每 HEARTBEAT_SEC 秒打印"已用Xs/预计Ys(Z%)"，证明没死。
- 全程同时写到 stderr 和持久 .log 文件，可 `tail -f <name>.transcript.log` 实时看。
环境变量：HEARTBEAT_SEC（默认 15）、TRANSCRIBE_RTF（默认 0.35）。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import wave

FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
HEARTBEAT_SEC = float(os.getenv("HEARTBEAT_SEC", "15"))
RTF = float(os.getenv("TRANSCRIBE_RTF", "0.35"))  # 本机实测 ~0.35×实时

# ---------- 日志机制 ----------
_T0 = time.time()
_LOGF = None  # 持久日志文件句柄


def _ts():
    return time.strftime("%H:%M:%S")


def log(*a):
    line = f"[{_ts()} +{time.time()-_T0:5.0f}s] " + " ".join(str(x) for x in a)
    print(line, file=sys.stderr, flush=True)
    if _LOGF:
        _LOGF.write(line + "\n")
        _LOGF.flush()


class stage:
    """阶段计时上下文。with stage('转码'): ... 自动打印开始/结束+耗时。"""
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.t = time.time()
        log(f"▶ {self.name} …")
        return self

    def __exit__(self, *exc):
        dt = time.time() - self.t
        log(f"{'✗' if exc[0] else '✓'} {self.name} 用时 {dt:.1f}s")


class heartbeat:
    """对长阻塞调用(如 FunASR generate)起心跳线程，证明进程还活着。"""
    def __init__(self, label, est_sec):
        self.label = label
        self.est = max(1.0, est_sec or 1.0)
        self._stop = threading.Event()

    def __enter__(self):
        self.t = time.time()
        log(f"▶ {self.label}（预计 ~{self.est:.0f}s）…")

        def loop():
            while not self._stop.wait(HEARTBEAT_SEC):
                e = time.time() - self.t
                pct = min(99, int(e / self.est * 100))
                eta = max(0, self.est - e)
                log(f"  ⏳ {self.label} 运行中… 已用 {e:.0f}s / 预计 ~{self.est:.0f}s ({pct}%, 还剩 ~{eta:.0f}s)")
        self._th = threading.Thread(target=loop, daemon=True)
        self._th.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        log(f"✓ {self.label} 完成，用时 {time.time()-self.t:.1f}s")


def wav_duration(path):
    try:
        with wave.open(path, "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return 0.0


def fmt_ts(sec):
    sec = max(0, int(sec))
    return f"{sec // 60:02d}:{sec % 60:02d}"


def to_wav(src):
    """ffmpeg → 16k 单声道 wav（所有引擎统一吃这个）。"""
    if not (shutil.which("ffmpeg") or os.path.exists(FFMPEG)):
        sys.exit("ffmpeg 未找到。brew install ffmpeg")
    fd, wav = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    with stage("① ffmpeg 转码 → 16k 单声道 wav"):
        subprocess.run(
            [FFMPEG, "-y", "-i", src, "-ac", "1", "-ar", "16000", "-vn", wav],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    return wav


# ---------- 引擎实现：各返回 [{start, end, text, spk}]（秒；spk 可为 None） ----------

def engine_available(name):
    try:
        if name == "funasr":
            __import__("funasr"); return True
        if name == "mlx":
            __import__("mlx_whisper"); return True
        if name == "groq":
            return bool(os.getenv("GROQ_API_KEY"))
        if name == "dashscope":
            return bool(os.getenv("DASHSCOPE_API_KEY"))
    except Exception:
        return False
    return False


def run_funasr(wav, diar=True):
    from funasr import AutoModel  # noqa
    with stage("② FunASR 模型加载（首次会下载到 ~/.cache/modelscope）"):
        kw = dict(model="paraformer-zh", vad_model="fsmn-vad", punc_model="ct-punc",
                  disable_update=True, disable_pbar=True, disable_log=True)
        if diar:
            kw["spk_model"] = "cam++"  # 集成说话人分离
        model = AutoModel(**kw)
    out = []
    res = model.generate(input=wav, batch_size_s=300, return_spk_res=diar,
                         disable_pbar=True)
    r0 = res[0] if isinstance(res, list) else res
    info = r0.get("sentence_info")
    if info:  # 句级带时间戳(+spk)
        for s in info:
            out.append({
                "start": s.get("start", 0) / 1000.0,
                "end": s.get("end", 0) / 1000.0,
                "text": (s.get("text") or "").strip(),
                "spk": s.get("spk"),
            })
    else:  # 退化：整段
        out.append({"start": 0, "end": 0, "text": (r0.get("text") or "").strip(), "spk": None})
    return [s for s in out if s["text"]]


def run_mlx(wav, **_):
    import mlx_whisper  # noqa
    r = mlx_whisper.transcribe(
        wav, path_or_hf_repo="mlx-community/whisper-large-v3-mlx", language="zh",
        verbose=False)
    return [{"start": s["start"], "end": s["end"], "text": s["text"].strip(), "spk": None}
            for s in r.get("segments", []) if s.get("text", "").strip()]


def run_groq(wav, **_):
    from groq import Groq  # noqa
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    with open(wav, "rb") as f:
        r = client.audio.transcriptions.create(
            model="whisper-large-v3", file=f, language="zh",
            response_format="verbose_json")
    segs = getattr(r, "segments", None) or (r.get("segments") if isinstance(r, dict) else [])
    out = []
    for s in segs:
        g = (lambda k: s.get(k) if isinstance(s, dict) else getattr(s, k))
        out.append({"start": g("start"), "end": g("end"), "text": g("text").strip(), "spk": None})
    return [s for s in out if s["text"]]


def run_dashscope(wav, **_):
    """阿里 DashScope SenseVoice。需 DASHSCOPE_API_KEY。"""
    import dashscope  # noqa
    from dashscope.audio.asr import Recognition  # noqa
    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
    rec = Recognition(model="paraformer-realtime-v2", format="wav",
                      sample_rate=16000, language_hints=["zh", "en"], callback=None)
    result = rec.call(wav)
    out = []
    for s in (result.get_sentence() or []):
        out.append({"start": s.get("begin_time", 0) / 1000.0,
                    "end": s.get("end_time", 0) / 1000.0,
                    "text": (s.get("text") or "").strip(), "spk": None})
    return [s for s in out if s["text"]]


ENGINES = {"funasr": run_funasr, "mlx": run_mlx, "groq": run_groq, "dashscope": run_dashscope}
AUTO_ORDER = ["funasr", "mlx", "groq", "dashscope"]


def maybe_pyannote_diar(wav, segs):
    """没有内置说话人(spk 全 None)时，尝试 pyannote 给 segment 贴 speaker。需 HF_TOKEN。"""
    if any(s.get("spk") is not None for s in segs):
        return segs
    if not os.getenv("HF_TOKEN"):
        return segs
    try:
        from pyannote.audio import Pipeline  # noqa
    except Exception:
        return segs
    try:
        with stage("②b pyannote 说话人分离"):
            pipe = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1",
                                            use_auth_token=os.getenv("HF_TOKEN"))
            diar = pipe(wav)
            turns = [(t.start, t.end, lbl) for t, _, lbl in diar.itertracks(yield_label=True)]
            for s in segs:
                mid = (s["start"] + s["end"]) / 2
                best, blbl = 0, None
                for a, b, lbl in turns:
                    ov = max(0, min(b, s["end"]) - max(a, s["start"]))
                    if ov > best:
                        best, blbl = ov, lbl
                if blbl is None:
                    for a, b, lbl in turns:
                        if a <= mid <= b:
                            blbl = lbl; break
                s["spk"] = blbl
    except Exception as e:
        log(f"pyannote 失败，跳过分离: {e}")
    return segs


def normalize_spk(segs):
    """把任意 spk 标签映射成 Speaker 1/2/3…（按首次出现顺序）。"""
    mapping, n = {}, 0
    for s in segs:
        k = s.get("spk")
        if k is None:
            s["speaker"] = "Speaker ?"
            continue
        if k not in mapping:
            n += 1; mapping[k] = n
        s["speaker"] = f"Speaker {mapping[k]}"
    return segs, n


def write_outputs(segs, n_spk, src, out_md):
    base = os.path.splitext(out_md)[0]
    merged = []
    for s in segs:
        if merged and merged[-1]["speaker"] == s["speaker"] and s["start"] - merged[-1]["end"] < 2:
            merged[-1]["text"] += ("" if merged[-1]["text"].endswith(("。", "！", "？", ".", "!", "?")) else " ") + s["text"]
            merged[-1]["end"] = s["end"]
        else:
            merged.append(dict(s))
    lines = [
        f"# Transcript — {os.path.basename(src)}",
        "",
        f"- 来源: `{src}`",
        f"- 段数: {len(merged)}  说话人数: {n_spk if n_spk else '未分离'}",
        "- speakers labeled Speaker N — who is founder/investor is decided in the analysis step",
        "",
        "---",
        "",
    ]
    for s in merged:
        lines.append(f"**[{fmt_ts(s['start'])}] {s['speaker']}:** {s['text']}")
        lines.append("")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    with open(base + ".json", "w", encoding="utf-8") as f:
        json.dump({"source": src, "n_speakers": n_spk, "segments": merged},
                  f, ensure_ascii=False, indent=2)
    log(f"✓ 写出 {out_md}")
    log(f"✓ 写出 {base}.json")


def main():
    global _LOGF
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--out")
    ap.add_argument("--engine", default="auto",
                    choices=["auto", "funasr", "mlx", "groq", "dashscope"])
    ap.add_argument("--no-diar", action="store_true")
    args = ap.parse_args()

    src = os.path.abspath(args.audio)
    if not os.path.exists(src):
        sys.exit(f"找不到文件: {src}")
    out_md = args.out or (os.path.splitext(src)[0] + ".transcript.md")

    # 打开持久日志
    logp = os.path.splitext(out_md)[0] + ".log"
    try:
        os.makedirs(os.path.dirname(logp) or ".", exist_ok=True)
        _LOGF = open(logp, "w", encoding="utf-8")
    except Exception:
        _LOGF = None
    log(f"=== transcribe 开始 ===  源: {os.path.basename(src)}")
    log(f"日志文件: {logp}（可 `tail -f` 实时看）")

    # 选引擎
    if args.engine == "auto":
        chosen = next((e for e in AUTO_ORDER if engine_available(e)), None)
        if not chosen:
            sys.exit(
                "没有可用转录引擎。装本地栈：\n"
                "  bash scripts/setup.sh\n"
                "或走 API：export GROQ_API_KEY=... / export DASHSCOPE_API_KEY=...")
    else:
        chosen = args.engine
        if not engine_available(chosen):
            sys.exit(f"引擎 {chosen} 不可用（未安装或缺 API key）。")
    log(f"引擎 = {chosen}  说话人分离 = {'否' if args.no_diar else '是'}")

    wav = to_wav(src)
    dur = wav_duration(wav)
    est = dur * RTF + (25 if chosen == "funasr" else 5)  # +模型加载粗估
    if dur:
        log(f"音频时长 {fmt_ts(dur)}（{dur/60:.1f} 分钟）→ 预计转录 ~{est/60:.1f} 分钟（RTF≈{RTF}）")
    try:
        with heartbeat("③ 转录 + 说话人分离", est):
            segs = ENGINES[chosen](wav, diar=not args.no_diar)
            if not args.no_diar:
                segs = maybe_pyannote_diar(wav, segs)
    finally:
        try:
            os.remove(wav)
        except OSError:
            pass

    if not segs:
        sys.exit("转录结果为空。")
    with stage("④ 合成（归并相邻同说话人 + 写文件）"):
        segs, n_spk = normalize_spk(segs)
        write_outputs(segs, n_spk, src, out_md)

    total = time.time() - _T0
    real_rtf = total / dur if dur else 0
    log(f"=== 完成 ===  共 {len(segs)} 段 / {n_spk} 位说话人 / 总耗时 {total:.0f}s"
        + (f"（实际 RTF≈{real_rtf:.2f}）" if dur else ""))
    if _LOGF:
        _LOGF.close()
    print(out_md)  # stdout = 产物路径，方便上层捕获


if __name__ == "__main__":
    main()
