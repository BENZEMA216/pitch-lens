# PitchLens Rubric (v2) — operational checklist

The step‑by‑step the analyst (LLM) executes. Narrative rationale: [`methodology.md`](methodology.md). Startup‑specific grounding: your `pitch-brief.md`.

## 0a · Meeting‑TYPE classifier
By "**who is being graded?**": you (raising) → **A Investor**; the counterparty (selling you their FA/advisory service) → **B FA**; both → **C Hybrid**; neither (co‑founder sync, customer/user interview, BD, press) → **D Other** (skip scoring; output Header + Summary + Extraction only, and say why).

## 0b · Meeting‑STAGE classifier (for A/C — pick the stage, use that card)
- **Intro / first (exploratory)** — first contact, they introduce themselves/portfolio, casual, no valuation/terms. → first‑meeting card.
- **Socialization / 2nd** — they bring a colleague / will repeat it internally.
- **Deep‑dive / product** — drilling data/product/tech. → deep‑dive card.
- **Partner meeting** — multiple partners, read a memo, multi‑angle grilling, decision timing. → partner card.
- **Closing** — valuation/terms/paper.
> Record the stage + your evidence in the Header. When unsure, label "first (exploratory)" and say so.

---

## 1 · Verdict (TOP signal — write first)
1. **Was a concrete, dated next step secured?** (2nd meeting / partner meeting / diligence / intro = yes; "stay in touch" = no = soft pass.)
2. **Who proposed it?** Investor‑proposed ≫ founder‑proposed.
3. **Temperature (by ACTIONS):** `COMMITTED‑WARM` (terms / check‑size / data‑room / intro / dated step / investor riffing) · `ENGAGED‑WARM` (deep + warm, no action) · `POLITE‑WARM` (short + nice, no step) · `COLD` (stated mismatch / fixates on one kill‑shot / generic praise + no step).

## 2 · Objective panel (compute from the diarized transcript)
- **Founder talk‑ratio** (sum all your speakers): first‑meeting ~⅓ healthy; overall 43–57%; **>65% → pitch‑dump flag**.
- **Investor talk‑ratio + turns**; flag if they riff on upside (timestamp it).
- **Longest single monologue** (either side): **>150 s → flag**.
- **Per‑speaker delivery** (for each of your speakers, track across meetings): **pace** (de‑punctuated chars/sec — comfortable Mandarin ~4–5.5, >6 fast; or words/min, target ~170), **hedging density** (count `maybe / I think / a bit / sort of / kind of` and locale equivalents — this is the credibility leak, not filler), **longest monologue**.
- **Question types (SPIN)** both sides; **sentiment/topic shift** timestamps; **proactive risk disclosure** (did the founder name competitors/CAC/regulation before being asked → +trust).

> Script to compute talk‑ratio / monologue / pace / hedging from the `*.transcript.json`: see the snippet at the bottom of this file.

## 3 · Stage scorecard (score ONLY this stage's dimensions, 0–10, each with quote + timestamp + "what a 10 looks like")
**First (exploratory) card:** 1) team credibility / founder‑market fit 2) **earned a next step** (+ did they ask the investor's process/concerns at the end) 3) read the **real gating** doubt 4) led with the strongest card (no buried lede) 5) clarity test (could a layperson restate what you do?) 6) chemistry (did the investor riff / offer intros). **Do NOT score** valuation/Series‑A/data‑room here.
**Deep‑dive card:** altitude‑shift · numbers cold · objection handling · the right person leading the technical thread · responsiveness to homework.
**Partner card:** interruption handling · a clean direct ask + decision timeline · depth under multi‑angle grilling · authentic energy.
> End with a weighted overall + the **fairness floor** (§5).

## 4 · Team dynamics (separate from content; uses diarization + your team ownership map)
Single narrator? · clean Q&A routing? · interruptions / steamrolling / contradictions (count) · per‑speaker talk share (is a key founder too quiet / the CEO silent?) · stage‑appropriate lineup. Use the ownership map in `pitch-brief.md` to judge "who *should* have answered this."

## 5 · Mutual‑qualification (did you interview them?)
Red/Yellow/Green (Green needs an investor quote): thesis fit · value‑add beyond capital · decision process + timeline · check size / lead‑vs‑follow · source of funds · founder references. Then **investor quality = STRONG / MIXED / WEAK**. Fundraising‑MEDDIC: economic buyer reached? champion forming? competition (other investors / their "do nothing") surfaced?

## 6 · Fairness floor + real gating
- **Fairness floor:** genuine engagement (long + deep + intro offer) and no stated structural pass → overall **floors at 5.5–6.0**, noted "good relationship signal, conviction pending." Never invert (don't score an engaged 80‑min meeting below a 15‑min brush‑off).
- **Real gating question:** the question they kept circling. State it in its own section; next‑meeting prep targets it.

## 7 · Regional calibration
Adapt to the market. (China/HK: reward relationship‑building in early meetings, don't punish a soft exploratory first meeting, reward direct handling of regulation/CAC, note WeChat‑live vs email‑formal follow‑up. Set your own market's norms here.)

---

## 8 · Output template v2 (fixed sections; "N/A — reason" rather than delete; diff‑able)
```
1  Header           type + STAGE + counterparty + your goal + classifier evidence
2  Verdict          dated next step? who proposed? · temperature (by actions) · score (fairness floor applied)
3  Summary          ≤200 words, neutral chronology
4  Objective panel  talk‑ratio (both) · longest monologue · per‑speaker pace+hedging · SPIN · sentiment shifts · risk disclosure
5  Stage scorecard  only this stage's dimensions | score/10 | quote+timestamp | what a 10 looks like
6  Team dynamics    single narrator · Q&A routing · interruptions/contradictions · per‑speaker share · lineup
7  Mutual‑qual      did you qualify them (R/Y/G) + investor quality STRONG/MIXED/WEAK + MEDDIC
8  Real gating Q    the question behind the question + the next step that addresses it
9  Extraction       action items (you / them) · commitments (verbatim) · follow‑ups w/ dates · open questions · ⭐ what you should have said but didn't (unused metrics, un‑pre‑empted kill‑shots, self‑owns committed)
10 48h follow‑up    a draft that adds NEW info (milestone / round filling) — not "just checking in" — + next‑meeting role plan
11 Quotes           3–8 verbatim, timestamped: strongest objection, strongest signal, any commitment, any self‑own
```

## 9 · FA‑meeting card (type B) — 6 dimensions, each with red flags, end with GO / NEGOTIATE / PASS
1) track record & stage/sector fit (verifiable closes?) 2) investor‑network fit to *your* ideal‑investor profile 3) terms (retainer / success fee — market ~2–5% at seed / exclusivity / tail‑lockup) 4) alignment & conflicts (do they push back like a partner, or flatter to win the mandate? other clients?) 5) process & value‑add beyond intros 6) mutual fit / cultural & cross‑border match. Red flags: vague "great relationships" with no named closes; success fee >5–7%; broad/indefinite exclusivity or long tail; double‑dipping on your own warm leads; running 15+ concurrent mandates.

---

## 10 · Compute objective signals (drop‑in)
```python
import json, re
segs = json.load(open("meeting.transcript.json"))["segments"]
clean = lambda t: re.sub(r"[，。、？！,.\s]", "", t)
HEDGE = ["maybe","i think","a bit","sort of","kind of","可能","一些","一点","比较","大概","我觉得","应该","有点"]
tot = sum(s["end"]-s["start"] for s in segs)
for sp in sorted({s["speaker"] for s in segs}):
    ss = [s for s in segs if s["speaker"]==sp]
    c = sum(len(clean(s["text"])) for s in ss); dur = sum(s["end"]-s["start"] for s in ss) or 1
    lm = max(s["end"]-s["start"] for s in ss)
    h = sum(s["text"].lower().count(w) for s in ss for w in HEDGE)
    print(f"{sp}: talk {dur/tot*100:4.0f}%  pace {c/dur:.2f}/s  longest {lm:.0f}s  hedges/100 {h/max(c,1)*100:.1f}")
```
