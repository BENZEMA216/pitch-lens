#!/usr/bin/env python3
"""
runlog.py — 整条复盘流水线的可观测日志（转录耗时 / 各 agent·workflow 耗时 / 推送 / 总耗时）。

每场复盘一个 run_id，记录到：
  runs/logs/<run_id>.pipeline.log   人读时间线
  runs/logs/pipeline.jsonl          机读总账（每事件一行，跨场聚合用）

为什么不用"墙钟时间差"算阶段耗时：复盘常跨多个对话回合/隔天，墙钟会失真。
所以**每个阶段显式传 --secs（实测耗时）**，total = 各阶段实测之和（不受回合间隔影响）。

用法:
  runlog.py start <run_id> --src 录音.m4a [--type 投资人]
  runlog.py ingest-transcribe <run_id> <…transcript.log>     # 自动抽"总耗时/实际RTF"
  runlog.py stage <run_id> <名称> --secs N [--note "…"] [--status ok|fail]
  runlog.py done <run_id> [--note "…"]                        # 打印时间线+总计
  runlog.py summary [--n 10]                                  # 跨场聚合统计

示例（一场复盘）:
  runlog.py start m5 --src 新录音5.m4a --type 投资人
  runlog.py ingest-transcribe m5 runs/新录音5.transcript.log
  runlog.py stage m5 analyze --secs 0 --note "v2 INVESTOR/首次 7.0 COMMITTED-WARM"
  runlog.py stage m5 workflow:coaching --secs 294 --note "3 agents/232k tok"
  runlog.py stage m5 feishu-push --secs 6 --note "逐字稿+分析"
  runlog.py stage m5 index-update --secs 2
  runlog.py done m5 --note "投资人#4"
"""
import argparse
import json
import os
import re
import sys
import time

LOGDIR = os.getenv("PITCHLENS_LOGDIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runs", "logs")
LEDGER = os.path.join(LOGDIR, "pipeline.jsonl")


def _statep(rid):
    return os.path.join(LOGDIR, f"{rid}.state.json")


def _logp(rid):
    return os.path.join(LOGDIR, f"{rid}.pipeline.log")


def _hhmmss(s):
    s = int(round(s))
    return f"{s//3600}:{(s%3600)//60:02d}:{s%60:02d}" if s >= 3600 else f"{s//60:02d}:{s%60:02d}"


def _load(rid):
    try:
        return json.load(open(_statep(rid)))
    except Exception:
        return None


def _save(rid, st):
    json.dump(st, open(_statep(rid), "w"), ensure_ascii=False)


def _human(rid, line):
    with open(_logp(rid), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _ledger(ev):
    os.makedirs(LOGDIR, exist_ok=True)
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False) + "\n")


def cmd_start(a):
    os.makedirs(LOGDIR, exist_ok=True)
    st = {"run_id": a.run_id, "start_wall": time.time(), "sum": 0.0,
          "src": a.src or "", "type": a.type or ""}
    _save(a.run_id, st)
    head = (f"=== 流水线日志  run={a.run_id}  "
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} ===\n"
            f"源: {os.path.basename(a.src or '')}   类型: {a.type or '-'}\n"
            f"{'阶段':<18}{'实测耗时':>10}   备注")
    open(_logp(a.run_id), "w", encoding="utf-8").write(head + "\n")
    _ledger({"run": a.run_id, "ev": "start", "ts": time.time(),
             "src": a.src or "", "type": a.type or ""})
    print(f"▶ start run={a.run_id}")


def _record_stage(rid, name, secs, status="ok", note=""):
    st = _load(rid)
    if not st:
        sys.exit(f"无此 run（先 start）：{rid}")
    st["sum"] = st.get("sum", 0.0) + max(0.0, secs)
    _save(rid, st)
    mark = "✓" if status == "ok" else "✗"
    line = f"{mark} {name:<16}{_hhmmss(secs):>10}   {note}"
    _human(rid, line)
    _ledger({"run": rid, "ev": "stage", "stage": name, "secs": round(secs, 1),
             "status": status, "note": note, "ts": time.time()})
    print(line)


def cmd_stage(a):
    _record_stage(a.run_id, a.stage, a.secs if a.secs is not None else 0.0,
                  a.status, a.note or "")


def _parse_transcribe_log(txt):
    """从 transcribe 的 .log 文本里抽 (secs, note)：总耗时 / 实际 RTF / 段·人。纯函数，便于测试。"""
    m = re.search(r"总耗时\s*([0-9.]+)s", txt)
    secs = float(m.group(1)) if m else 0.0
    rtf = re.search(r"实际\s*RTF[≈~]?\s*([0-9.]+)", txt)
    seg = re.search(r"共\s*(\d+)\s*段\s*/\s*(\d+)\s*位", txt)
    note = []
    if seg:
        note.append(f"{seg.group(1)}段/{seg.group(2)}人")
    if rtf:
        note.append(f"RTF {rtf.group(1)}")
    return secs, " ".join(note)


def cmd_ingest_transcribe(a):
    """从 transcribe 的 .log 里抽 '总耗时 Xs' 和 '实际 RTF≈Y' 自动记一条 transcribe 阶段。"""
    try:
        txt = open(a.log, encoding="utf-8").read()
    except Exception as e:
        sys.exit(f"读不到 transcribe 日志: {e}")
    secs, note = _parse_transcribe_log(txt)
    _record_stage(a.run_id, "transcribe", secs, "ok", note)


def cmd_done(a):
    st = _load(a.run_id)
    if not st:
        sys.exit(f"无此 run：{a.run_id}")
    total = st.get("sum", 0.0)
    line = f"■ DONE  实测总计 {_hhmmss(total)}   {a.note or ''}"
    _human(a.run_id, line)
    _ledger({"run": a.run_id, "ev": "done", "total_secs": round(total, 1),
             "note": a.note or "", "ts": time.time()})
    print("\n" + open(_logp(a.run_id), encoding="utf-8").read().rstrip())


def cmd_summary(a):
    if not os.path.exists(LEDGER):
        sys.exit("还没有任何流水线日志。")
    runs = {}
    for ln in open(LEDGER, encoding="utf-8"):
        try:
            ev = json.loads(ln)
        except Exception:
            continue
        r = runs.setdefault(ev["run"], {"stages": {}, "total": None, "src": "", "type": ""})
        if ev["ev"] == "start":
            r["src"] = ev.get("src", ""); r["type"] = ev.get("type", "")
        elif ev["ev"] == "stage":
            r["stages"][ev["stage"]] = ev["secs"]
        elif ev["ev"] == "done":
            r["total"] = ev["total_secs"]
    done = [(k, v) for k, v in runs.items() if v["total"] is not None]
    done = done[-(a.n):]
    print(f"{'run':<14}{'类型':<8}{'transcribe':>11}{'workflow合计':>13}{'总计':>9}")
    tt = []
    for k, v in done:
        wf = sum(s for n, s in v["stages"].items() if n.startswith("workflow"))
        tr = v["stages"].get("transcribe", 0)
        tt.append(v["total"])
        print(f"{k:<14}{(v['type'] or '-'):<8}{_hhmmss(tr):>11}{_hhmmss(wf):>13}{_hhmmss(v['total']):>9}")
    if tt:
        print(f"\n共 {len(tt)} 场 · 平均总耗时 {_hhmmss(sum(tt)/len(tt))} · 总账 {LEDGER}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start"); s.add_argument("run_id"); s.add_argument("--src"); s.add_argument("--type"); s.set_defaults(fn=cmd_start)
    s = sub.add_parser("stage"); s.add_argument("run_id"); s.add_argument("stage"); s.add_argument("--secs", type=float); s.add_argument("--status", default="ok"); s.add_argument("--note"); s.set_defaults(fn=cmd_stage)
    s = sub.add_parser("ingest-transcribe"); s.add_argument("run_id"); s.add_argument("log"); s.set_defaults(fn=cmd_ingest_transcribe)
    s = sub.add_parser("done"); s.add_argument("run_id"); s.add_argument("--note"); s.set_defaults(fn=cmd_done)
    s = sub.add_parser("summary"); s.add_argument("--n", type=int, default=10); s.set_defaults(fn=cmd_summary)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
