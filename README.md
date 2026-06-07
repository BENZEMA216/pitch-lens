# PitchLens 🔎

**Turn your fundraising-meeting recordings into stable, comparable post-mortems.**

You just met an investor or an FA (financial advisor / 融资顾问). You won't remember whether the GP cooled off when you hit the moat question, which kill-shot you fumbled, or whether you talked too much. PitchLens takes the **recording** and produces a **structured, repeatable review** — so every meeting is scored the same way and you can compare across meetings over time.

> Product axiom (borrowed from trade journaling): **You don't have to remember it — we help you see it.**

It's two layers:

1. **Transcription** — local‑first (private), speaker‑labeled, timestamped. Especially strong for **Mandarin / code‑switched** audio (FunASR), with cloud fallbacks.
2. **Analysis** — a research‑backed framework (not a vibes score) that classifies the meeting, computes **objective signals** from the transcript, scores it on a **stage‑appropriate** rubric, reads the room **bidirectionally**, and writes a fixed‑format report you can diff across meetings.

The analysis is done by an **LLM** — ship it as a [Claude Code skill](#option-a--claude-code-skill-recommended) (drop a recording, get a report) or run the rubric with any model.

---

## Why it's different from "summarize my call"

Most tools dump a summary. PitchLens is opinionated about **fundraising meetings specifically**, and it fixes the mistakes a naive scorer makes:

| Naive scoring | PitchLens |
|---|---|
| Grades every meeting like a formal pitch | **Stage‑aware** — a casual first coffee is judged on "did you earn the next meeting", not "did you state the Series A trigger" |
| Subjective 0–10 vibes | **Objective signals** from the transcript — talk‑ratio, longest monologue, speaking pace, filler/hedge density, who proposed the next step |
| Only grades the founder | **Bidirectional** — did *you* qualify the investor (smart money? thesis fit? decision process?) |
| Treats the team as one "founder" | **Team module** — who held the floor, who should have answered what, talk distribution |
| "Investor was friendly = good" | **Temperature by actions** (a dated next step, terms, intros) — not by politeness |

The single most‑weighted outcome is **"did a concrete, dated next step get set, and who proposed it?"** (the fundraising analog of sales‑deal momentum).

---

## What you get

A fixed 11‑section report (so meetings are diff‑able):

```
1  Header          type (investor/FA) + STAGE + counterparty + your goal
2  Verdict         next step secured? who proposed it? · temperature (by actions) · score (with fairness floor)
3  Summary
4  Objective panel talk‑ratio · longest monologue · pace · question types · sentiment shifts
5  Stage scorecard only the dimensions that matter at THIS stage
6  Team dynamics   single narrator? Q&A routing? interruptions? talk distribution
7  Mutual‑qual     did you qualify the investor? + investor quality STRONG/MIXED/WEAK
8  Real gating Q    the "question behind the question" they kept circling
9  Extraction       action items · commitments · "what you should have said but didn't"
10 48h follow‑up    a momentum‑laden draft + next‑meeting role plan
11 Quotes
```

See [`examples/`](examples/) for a full synthetic example.

---

## How it works

```
recording / video / text
  └─ ① transcribe   scripts/transcribe.py  → [mm:ss] Speaker N: …  (+ .json, + .log w/ ETA & heartbeat)
  └─ ② classify     meeting TYPE (investor / FA / hybrid / other) × STAGE (intro / first / deep‑dive / partner / closing)
  └─ ③ analyze      objective signals + stage scorecard + team module + bidirectional, grounded in YOUR pitch brief
  └─ ④ report       the fixed 11‑section template above
  └─ ⑤ (optional)   publish to Feishu/Lark · log the run for observability
```

---

## Quickstart

```bash
git clone <your-fork-url> pitch-lens && cd pitch-lens

# 1. Install the local transcription stack (private, free, offline after first run)
bash scripts/setup.sh          # installs funasr + torch (+ optional extras)

# 2. Transcribe a recording  → meeting.transcript.md / .json / .log
python3 scripts/transcribe.py /path/to/meeting.m4a
#   watch progress live (ETA + heartbeat) in another shell:
#   tail -f /path/to/meeting.transcript.log
```

First run downloads ~1–2 GB of models to `~/.cache/modelscope`. After that it's offline. Roughly **0.35× real‑time** on Apple Silicon (a 60‑min recording ≈ 20 min).

### Step 3 — analyze

**Option A — Claude Code skill (recommended).** Copy `skill/` into your Claude Code skills dir and fill in your startup (see [Customize](#customize-for-your-startup)). Then just drop a recording and say *"review this investor meeting"* — it runs ①→④ and writes the report.

```bash
cp -r skill ~/.claude/skills/pitch-lens   # or wherever your agent loads skills
```

**Option B — any LLM.** Give your model the transcript + [`skill/reference/rubrics.md`](skill/reference/rubrics.md) + your filled‑in `pitch-brief.md`, and ask it to produce the 11‑section report.

### Step 4 (optional) — publish & log

- **Feishu/Lark:** turn each report into a shareable doc and keep a master index — see [`docs/feishu-integration.md`](docs/feishu-integration.md).
- **Observability:** `scripts/runlog.py` records per‑run timings (transcription / analysis / publish / total) to `runs/logs/` so you can answer "how long did each stage take, on average?".

---

## Customize for your startup

The framework is generic; the **grounding** is yours. Copy the template and fill it in once:

```bash
cp skill/reference/pitch-brief.template.md skill/reference/pitch-brief.md
# then edit: your one‑liner, thesis, the hard questions investors ask YOU + ideal answers,
# the metrics you should be citing, your known self‑owns, ideal investor, team ownership map.
```

`pitch-brief.md` is what makes the report say *"you fumbled question 3 and never deployed metric X"* instead of generic feedback. It's git‑ignored by default so your strategy stays private.

---

## Privacy

Fundraising recordings contain valuations, terms, and candid opinions. PitchLens is **local‑first by design** — transcription runs entirely on your machine (FunASR), nothing leaves it. Cloud ASR (Groq / DashScope) is **opt‑in** and clearly flagged. The `.gitignore` keeps recordings, transcripts, reports, and your pitch brief out of git.

---

## Repo layout

```
scripts/
  transcribe.py   audio → speaker‑labeled, timestamped transcript (local‑first, API fallback, ETA+heartbeat+log)
  runlog.py       per‑run pipeline observability (timings → runs/logs/)
  setup.sh        install the local transcription stack
skill/
  SKILL.md                       the runbook (a Claude Code skill)
  reference/
    methodology.md               WHY — the v2 analysis method (stage‑aware, objective signals, …)
    rubrics.md                   HOW — the operational rubric + fixed output template
    pitch-brief.template.md      fill this with YOUR startup
examples/                        a full synthetic transcript + report
docs/
  methodology.md                 the method, long form
  feishu-integration.md          optional: publish reports to Feishu/Lark
runs/                            your transcripts, reports & logs land here (git‑ignored)
```

---

## Credits

The analysis method stands on published work on conversation intelligence and fundraising:
Gong / Chorus (talk‑ratio, next‑steps, filler vs. hedging), MEDDIC, SPIN; NextView "VC Meeting Map", First Round, Paul Graham "How to Raise Money", Sequoia "How to Present", Michael Seibel / YC, a16z, Tomasz Tunguz; Mirabile / Belenzon on multi‑founder pitches; *Pyramid Principle*; *Executive Presence* (Hewlett). Full citations in [`docs/methodology.md`](docs/methodology.md).

Transcription: [FunASR](https://github.com/modelscope/FunASR) (Alibaba), with optional mlx‑whisper / Groq / DashScope.

## License

[MIT](LICENSE). Contributions welcome.
