---
name: pitch-lens
description: >-
  Turn a fundraising-meeting recording (investor or FA / 融资顾问) into a stable, comparable post-mortem.
  Fixed pipeline: transcribe + diarize → classify TYPE (investor/FA/hybrid/other) × STAGE (intro/first/deep-dive/partner/closing)
  → objective signals (talk-ratio, monologue, pace, hedging) + stage scorecard + team module + mutual-qualification
  → fixed 11-section report. Local-first transcription (private). Optionally publishes to Feishu/Lark and logs each run.
  Use when the user gives a recording/audio/transcript of an investor or FA meeting and asks to analyze / score / 复盘 / review it.
  Triggers: "review this investor meeting", "复盘这次见投资人", "分析这段录音", "score my pitch", "review this FA meeting",
  or the user drops an .m4a/.mp3/.wav/.mp4/.txt of a fundraising meeting.
---

# PitchLens — fundraising-meeting recording review

Turn every meeting recording into a **stable, comparable** review — same pipeline, same stage-appropriate rubric, same report. The point isn't one dazzling analysis; it's that meeting #3 is diff-able against meeting #1.

Method (why): `reference/methodology.md`. Rubric (how): `reference/rubrics.md`. Your grounding: `reference/pitch-brief.md` (copy from the template first).

## Pipeline (run all steps)
```
recording / video / text
 ① transcribe + diarize   scripts/transcribe.py → [mm:ss] Speaker N: …  (+ .json, + .log with ETA & heartbeat)
 ② classify TYPE + STAGE  投资人A/FA B/hybrid C/other D  ×  intro/first/deep-dive/partner/closing
 ③ analyze                objective signals + stage scorecard + team module + mutual-qualification (grounded in pitch-brief.md)
 ④ report                 the fixed 11-section template (rubrics.md §8)
 ⑤ (optional) publish + log
```

### ① Transcribe
```bash
python3 scripts/transcribe.py <audio/video> --out <name>.transcript.md
# live progress (ETA + 15s heartbeat): tail -f <name>.transcript.log
```
Engine auto-selects: local FunASR (best for Chinese, includes speaker diarization) → mlx-whisper → Groq API → DashScope. Local-first for privacy. If the user gives text/an existing transcript, skip ① → go to ②.

### ② Classify (iron rule: classify BEFORE scoring)
- **TYPE** by "who is being graded?" — you → A Investor; the counterparty selling advisory → B FA; both → C Hybrid; neither → D Other (lightweight summary only).
- **STAGE** (A/C) — intro / first(exploratory) / socialization / deep-dive / partner / closing. A casual first chat is scored on "did you earn the next meeting", NOT on valuation/Series-A. See `rubrics.md §0`.

### ③ Analyze
- **Verdict first:** dated next step? who proposed it? temperature by **actions** (not politeness).
- **Objective signals** from diarization (use the snippet in `rubrics.md §10`): talk-ratio (founder >65% = pitch dump), longest monologue (>150s flag), per-speaker pace + hedging density, SPIN question types, sentiment shifts.
- **Stage scorecard** — only this stage's dimensions, each with quote + timestamp.
- **Team module** + **mutual-qualification** (did you qualify the investor?), grounded in `pitch-brief.md`'s ownership map + question bank.
- **Fairness floor** + **real gating question**.

### ④ Report — fixed 11 sections (`rubrics.md §8`), order/titles constant, "N/A — reason" rather than delete.

## Iron rules (what makes it "stable")
1. Classify TYPE + STAGE before scoring; stage picks the card.
2. **Outcome first:** the top signal is a dated next step + who proposed it; temperature by actions, not words.
3. **Fairness floor:** genuine engagement + no structural pass → floor 5.5–6, never invert.
4. **Objective over vibes:** compute talk-ratio / monologue / pace / hedging; they're cross-meeting comparable.
5. Every claim gets a quote + timestamp; template sections never change → diff-able.
6. Find the **real gating question** (the one behind the question); prep targets it.
7. Save each report to `runs/<date>-<counterparty>.md` and keep an index for longitudinal comparison.
8. Write in the user's language; keep English terms and quotes verbatim.

## ⑤ Optional — publish & log
- **Feishu/Lark:** publish reports + maintain a master index — see `../docs/feishu-integration.md` (configure your own folder token; nothing is hardcoded).
- **Pipeline log:** `scripts/runlog.py start|ingest-transcribe|stage|done|summary` records per-run timings (transcribe / workflow / publish / total) → `runs/logs/`. (zsh: inline the command, don't `$RL start`.)

## Key files
- `reference/methodology.md` — WHY (the v2 method).
- `reference/rubrics.md` — HOW (operational checklist + fixed output template + signal-compute snippet).
- `reference/pitch-brief.md` — YOUR startup (copy from `pitch-brief.template.md`; git-ignored).
- `../scripts/` — transcribe.py (ETA/heartbeat/log), runlog.py, setup.sh.

> First time: `cp reference/pitch-brief.template.md reference/pitch-brief.md` and fill it in. Update the question bank after every meeting.
