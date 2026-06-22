#!/usr/bin/env python3
"""
transcribe.py — 把会议/对谈录音/视频（投资人/FA/客户/团队/访谈…）转成「带时间戳 + 说话人标签」的对话稿。

本地优先，云端兜底（云端默认不开，需显式 --engine 或 --allow-cloud）。引擎选择顺序（--engine auto）：
  funasr     本地，中文最强，含 VAD+标点+说话人分离(cam++)   ← 默认首选
  mlx        本地 mlx-whisper（Apple Silicon），多语强，无说话人
  groq       Groq Whisper-large-v3（API，需 GROQ_API_KEY），快，无说话人→可选 pyannote
  dashscope  阿里 Paraformer（API，需 DASHSCOPE_API_KEY），中文优化便宜，无说话人
  openrouter OpenRouter STT（API，需 OPENROUTER_API_KEY），可插拔多模型；**纯文本、无说话人分离**

⚠️ 隐私：funasr/mlx 本地，录音不出本机；groq/dashscope/openrouter 会**上传音频到云端**。
   因此 auto 默认只在本地引擎里选；要在 auto 里纳入云端，须加 --allow-cloud（每次云端调用前会显式告警）。

用法:
  python3 transcribe.py 录音.m4a
  python3 transcribe.py 录音.mp4 --out 录音.transcript.md --engine funasr
  python3 transcribe.py 录音.wav --engine openrouter            # 走 OpenRouter（纯文本，无分离）
  python3 transcribe.py 录音.m4a --allow-cloud                  # 本地不可用时允许 auto 回退到云端
  python3 transcribe.py 录音.m4a --no-diar                      # 跳过说话人分离
  python3 transcribe.py 录音.mp4 --language en                  # 指定语种（默认 zh；auto=自动识别）

输出: <name>.transcript.md（人读） + <name>.transcript.json（机读，毫秒时间戳+spk）
     + <name>.transcript.log（结构化日志：每阶段耗时、ETA、心跳）  ← v2 日志机制

说话人分离：只有 funasr(cam++) 与 pyannote(需 HF_TOKEN) 路径会产出真实说话人；其余引擎 spk=None。
若最终 < 2 位说话人，会**显式告警**——此时 talk-ratio / 分人语速 / 团队动态等客观信号不可计算，
报告里相关面板应标 "N/A — 无说话人分离"，不要凭单桶文本编造客观信号。

日志（解决"卡在结构化看不到进度"）：
- 启动即打印音频时长 + 预计耗时(ETA, 本机 RTF≈0.35)。
- 每个阶段(转码/模型加载/转录+分离/合成写出)单独计时。
- 转录是单次阻塞调用 → 起一个**心跳线程**，每 HEARTBEAT_SEC 秒打印"已用Xs/预计Ys(Z%)"，证明没死。
- 全程同时写到 stderr 和持久 .log 文件，可 `tail -f <name>.transcript.log` 实时看。
环境变量：HEARTBEAT_SEC（默认 15）、TRANSCRIBE_RTF（默认 0.35）、
         OPENROUTER_ASR_MODEL（默认 openai/whisper-large-v3，中文可设 qwen/qwen3-asr-flash）、
         FFMPEG_BIN（手动指定 ffmpeg 路径）。
"""
import argparse
import base64
import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import wave

FFMPEG = shutil.which("ffmpeg") or os.getenv("FFMPEG_BIN")
HEARTBEAT_SEC = float(os.getenv("HEARTBEAT_SEC", "15"))
RTF = float(os.getenv("TRANSCRIBE_RTF", "0.35"))  # 本机实测 ~0.35×实时
MERGE_GAP_SEC = 2.0  # 同说话人、间隔 < 此值的相邻段，在人读稿里合并（仅影响 .md 可读性）

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


def _whisper_lang(lang):
    """把 --language 归一成 whisper 系引擎的语种参数。默认中文优先；'auto' → None(自动识别)。"""
    if not lang:
        return "zh"
    if lang == "auto":
        return None
    return lang


def to_wav(src):
    """ffmpeg → 16k 单声道 wav（所有引擎统一吃这个；云端分离也要求单声道）。"""
    if not FFMPEG:
        sys.exit("ffmpeg 未找到 / not found。安装：brew install ffmpeg（macOS）或 apt install ffmpeg（Linux），"
                 "或设 FFMPEG_BIN 指向可执行文件。")
    fd, wav = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        with stage("① ffmpeg 转码 → 16k 单声道 wav"):
            subprocess.run(
                [FFMPEG, "-y", "-i", src, "-ac", "1", "-ar", "16000", "-vn", wav],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
    except Exception:
        try:
            os.remove(wav)  # 转码失败别留下 0 字节临时文件
        except OSError:
            pass
        raise
    return wav


# ---------- 引擎实现：各返回 [{start, end, text, spk}]（秒；spk 可为 None） ----------

def engine_available(name):
    """本地引擎要求可 import；云端引擎要求 同时 有 key 且包已安装（避免 key 在但包没装 → 转码后才崩）。"""
    try:
        if name == "funasr":
            return importlib.util.find_spec("funasr") is not None
        if name == "mlx":
            return importlib.util.find_spec("mlx_whisper") is not None
        if name == "groq":
            return bool(os.getenv("GROQ_API_KEY")) and importlib.util.find_spec("groq") is not None
        if name == "dashscope":
            return bool(os.getenv("DASHSCOPE_API_KEY")) and importlib.util.find_spec("dashscope") is not None
        if name == "openrouter":
            return bool(os.getenv("OPENROUTER_API_KEY")) and importlib.util.find_spec("requests") is not None
    except Exception:
        return False
    return False


def run_funasr(wav, diar=True, lang=None, **_):
    if lang and lang not in ("zh", "auto"):
        log(f"⚠️  funasr 仅支持中文，已忽略 --language {lang}。")
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


def run_mlx(wav, lang=None, **_):
    import mlx_whisper  # noqa
    r = mlx_whisper.transcribe(
        wav, path_or_hf_repo="mlx-community/whisper-large-v3-mlx",
        language=_whisper_lang(lang), verbose=False)
    return [{"start": s["start"], "end": s["end"], "text": s["text"].strip(), "spk": None}
            for s in r.get("segments", []) if s.get("text", "").strip()]


def run_groq(wav, lang=None, **_):
    from groq import Groq  # noqa
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    lw = _whisper_lang(lang)
    kw = dict(model="whisper-large-v3", response_format="verbose_json")
    if lw:
        kw["language"] = lw
    with open(wav, "rb") as f:
        r = client.audio.transcriptions.create(file=f, **kw)
    segs = getattr(r, "segments", None) or (r.get("segments") if isinstance(r, dict) else [])
    out = []
    for s in segs:
        g = (lambda k: s.get(k) if isinstance(s, dict) else getattr(s, k))
        out.append({"start": g("start"), "end": g("end"), "text": g("text").strip(), "spk": None})
    return [s for s in out if s["text"]]


def run_dashscope(wav, lang=None, **_):
    """阿里 DashScope Paraformer。需 DASHSCOPE_API_KEY。
    注意：当前用实时识别器(Recognition)做离线文件转写——对长录音不理想，且不返回说话人分离。
    TODO（见 Base 改进项 P0/P2）：切到 Transcription.async_call(model='paraformer-v2',
    diarization_enabled=True, speaker_count=<hint>) 以拿到原生说话人分离 + ms 时间戳。"""
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


OPENROUTER_URL = "https://openrouter.ai/api/v1/audio/transcriptions"
OR_CHUNK_SEC = int(os.getenv("OPENROUTER_CHUNK_SEC", "120"))  # 长音频按此切片（上游响应有 ~60s 超时）


def _openrouter_one(wav_path, model, lang):
    """单段调用 OpenRouter STT：JSON body + base64(input_audio)，只回 text（无时间戳/分离）。"""
    import requests  # noqa
    b64 = base64.b64encode(open(wav_path, "rb").read()).decode()
    body = {"model": model, "input_audio": {"data": b64, "format": "wav"}}
    lw = _whisper_lang(lang)
    if lw:
        body["language"] = lw
    r = requests.post(
        OPENROUTER_URL,
        headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                 "Content-Type": "application/json"},
        json=body, timeout=180)
    r.raise_for_status()
    j = r.json()
    return (j.get("text") or "").strip() if isinstance(j, dict) else ""


def run_openrouter(wav, diar=True, lang=None, **_):
    """OpenRouter STT（POST /audio/transcriptions，JSON+base64）。需 OPENROUTER_API_KEY。
    模型默认 openai/gpt-4o-transcribe（中文最干净），可用 OPENROUTER_ASR_MODEL 覆盖
    （openai/whisper-large-v3 更便宜；openai/whisper-large-v3-turbo 最快但易幻听）。
    ⚠️ 该端点只回纯文本——**无说话人分离、无逐句时间戳**。长音频按 OPENROUTER_CHUNK_SEC 切片，
       每片给一个粗粒度 [start,end] 时间窗（非逐句）。要真实分离请用 funasr 或 HF_TOKEN+pyannote。"""
    model = os.getenv("OPENROUTER_ASR_MODEL", "openai/gpt-4o-transcribe")
    dur = wav_duration(wav)
    out = []
    if dur <= OR_CHUNK_SEC + 1:
        txt = _openrouter_one(wav, model, lang)
        if txt:
            out.append({"start": 0.0, "end": dur or 0.0, "text": txt, "spk": None})
    else:
        n = math.ceil(dur / OR_CHUNK_SEC)
        log(f"OpenRouter STT 分片：{dur:.0f}s → {n} 段 × {OR_CHUNK_SEC}s（模型 {model}）")
        for i in range(n):
            ss = i * OR_CHUNK_SEC
            ee = min(ss + OR_CHUNK_SEC, dur)
            chunk = f"{wav}.part{i}.wav"
            subprocess.run([FFMPEG, "-y", "-ss", str(ss), "-t", str(OR_CHUNK_SEC), "-i", wav,
                            "-ac", "1", "-ar", "16000", chunk],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                txt = _openrouter_one(chunk, model, lang)
            finally:
                try:
                    os.remove(chunk)
                except OSError:
                    pass
            if txt:
                out.append({"start": float(ss), "end": float(ee), "text": txt, "spk": None})
            log(f"  ✓ 片段 {i+1}/{n}（{fmt_ts(ss)}–{fmt_ts(ee)}）")
    if diar:
        log("⚠️  OpenRouter STT 无说话人分离：talk-ratio / 分人指标不可计算"
            "（如需分离，设 HF_TOKEN 走 pyannote，或改用 funasr / 带分离的云端引擎）。")
    return [s for s in out if s["text"]]


ENGINES = {"funasr": run_funasr, "mlx": run_mlx, "groq": run_groq,
           "dashscope": run_dashscope, "openrouter": run_openrouter}
LOCAL_ENGINES = ["funasr", "mlx"]            # 录音不出本机
CLOUD_ENGINES = ["groq", "dashscope", "openrouter"]  # 会上传音频到云端
AUTO_ORDER = LOCAL_ENGINES + CLOUD_ENGINES   # 完整优先级；云端仅在 --allow-cloud 时纳入 auto


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


def transcribe_with_fallback(wav, candidates, diar, lang=None):
    """按 candidates 顺序逐个尝试；某引擎抛异常或返回空 → 记录并回退到下一个。
    返回 (成功的引擎名, segs)；全部失败返回 (None, [])。"""
    dur = wav_duration(wav)
    last_err = None
    for eng in candidates:
        if eng in CLOUD_ENGINES:
            log(f"⚠️  即将上传音频到云端（{eng}）——录音会离开本机。")
        est = dur * RTF + (25 if eng == "funasr" else 5)  # +模型加载粗估
        try:
            with heartbeat(f"③ 转录[{eng}] + 说话人分离", est):
                segs = ENGINES[eng](wav, diar=diar, lang=lang)
                if diar:
                    segs = maybe_pyannote_diar(wav, segs)
            if segs:
                return eng, segs
            log(f"✗ 引擎 {eng} 返回空结果，尝试下一个候选…")
        except Exception as e:
            last_err = e
            log(f"✗ 引擎 {eng} 失败：{e!r}；尝试下一个候选…")
    if last_err:
        log(f"所有候选引擎均失败，最后错误：{last_err!r}")
    return None, []


def merge_adjacent(segs):
    """把相邻、同说话人、间隔 < MERGE_GAP_SEC 的段合并（仅为人读稿的可读性）。
    不吞负间隔（乱序/重叠段），合并后 end 取 max 防止时间戳倒退。"""
    merged = []
    for s in segs:
        gap = s["start"] - merged[-1]["end"] if merged else None
        # never merge unknown speakers ("Speaker ?") — we can't claim they're the same person,
        # and merging would collapse the only timestamps a no-diarization engine produces.
        same_known = (merged and merged[-1]["speaker"] == s["speaker"] and s["speaker"] != "Speaker ?")
        if same_known and gap is not None and 0 <= gap < MERGE_GAP_SEC:
            tail = merged[-1]["text"]
            sep = "" if tail.endswith(("。", "！", "？", ".", "!", "?")) else " "
            merged[-1]["text"] = tail + sep + s["text"]
            merged[-1]["end"] = max(merged[-1]["end"], s["end"])
        else:
            merged.append(dict(s))
    return merged


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
    merged = merge_adjacent(segs)
    if n_spk >= 2:
        spk_line = f"说话人数: {n_spk}"
    else:
        spk_line = ("说话人数: <2 ⚠️ 未获得说话人分离 → talk-ratio / 分人语速 / 团队动态 "
                    "不可计算，报告相关面板请标 'N/A — 无说话人分离'")
    lines = [
        f"# Transcript — {os.path.basename(src)}",
        "",
        f"- 来源: `{src}`",
        f"- 段数: {len(merged)}  {spk_line}",
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
                    choices=["auto", "funasr", "mlx", "groq", "dashscope", "openrouter"])
    ap.add_argument("--language", default="zh",
                    help="语种（默认 zh；auto=自动识别；funasr 仅中文）")
    ap.add_argument("--allow-cloud", action="store_true",
                    help="允许 auto 在本地引擎不可用时回退到云端（会上传音频）")
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

    # 选引擎 → 候选列表（auto 默认仅本地；--allow-cloud 才纳入云端）
    if args.engine == "auto":
        pool = AUTO_ORDER if args.allow_cloud else LOCAL_ENGINES
        candidates = [e for e in pool if engine_available(e)]
        if not candidates:
            extra = "" if args.allow_cloud else "\n或加 --allow-cloud 允许 auto 回退到云端引擎。"
            sys.exit(
                "没有可用的本地转录引擎。装本地栈：\n"
                "  bash scripts/setup.sh\n"
                "或走云端（显式指定）：--engine groq|dashscope|openrouter\n"
                "  export GROQ_API_KEY=... / DASHSCOPE_API_KEY=... / OPENROUTER_API_KEY=..."
                + extra)
    else:
        if not engine_available(args.engine):
            sys.exit(f"引擎 {args.engine} 不可用（未安装或缺 API key）。")
        candidates = [args.engine]  # 显式指定 = 严格，不回退

    log(f"候选引擎 = {candidates}  说话人分离 = {'否' if args.no_diar else '是'}  语种 = {args.language}")

    wav = to_wav(src)
    dur = wav_duration(wav)
    if dur:
        est = dur * RTF + 25
        log(f"音频时长 {fmt_ts(dur)}（{dur/60:.1f} 分钟）→ 预计转录 ~{est/60:.1f} 分钟（RTF≈{RTF}）")
    try:
        eng, segs = transcribe_with_fallback(wav, candidates, not args.no_diar, args.language)
    finally:
        try:
            os.remove(wav)
        except OSError:
            pass

    if not segs:
        sys.exit("转录失败：所有候选引擎都没有产出结果。")
    log(f"✓ 实际使用引擎 = {eng}")

    with stage("④ 合成（归并相邻同说话人 + 写文件）"):
        segs, n_spk = normalize_spk(segs)
        write_outputs(segs, n_spk, src, out_md)

    if n_spk < 2:
        log("⚠️  最终 < 2 位说话人：客观信号面板 / 团队动态不可计算；分析阶段相关章节应标 N/A。")

    total = time.time() - _T0
    real_rtf = total / dur if dur else 0
    log(f"=== 完成 ===  共 {len(segs)} 段 / {n_spk} 位说话人 / 总耗时 {total:.0f}s"
        + (f"（实际 RTF≈{real_rtf:.2f}）" if dur else ""))
    if _LOGF:
        _LOGF.close()
    print(out_md)  # stdout = 产物路径，方便上层捕获


if __name__ == "__main__":
    main()
