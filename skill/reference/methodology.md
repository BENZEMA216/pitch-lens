# PitchLens Methodology (v2)

How PitchLens turns a fundraising‑meeting recording into a **stable, comparable** review — and why it scores the way it does. This is the reusable framework; the startup‑specific grounding lives in your `pitch-brief.md`.

---

## Part 1 · Why naive pitch scoring is wrong

A "summarize + rate 0–10" approach makes five mistakes, and they compound:

| Blindness | Failure |
|---|---|
| **Modality** | Applies a formal‑pitch checklist to a casual get‑to‑know‑you meeting; punishes "didn't lead with the thesis in 5 min" when discovering chemistry was the point. |
| **Perspective** | Only grades the founder; ignores that you are *also* evaluating the investor (smart money? domain fit? would you want them on your cap table?). |
| **Stage** | First coffee vs. partner meeting vs. closing are judged identically; "state the Series A trigger" is irrelevant in a first chat. |
| **Team** | Grades "the founder" monolithically; misses who held the floor, who should have fielded which question. |
| **Canned‑answer bias** | Rewards "did you deploy the memorized answer" over "did you read the room, surface the real objection, and earn the next meeting." |

The result is an inverted, demoralizing score: a genuinely productive 80‑minute relationship meeting (investor stayed engaged, offered intros) gets marked *down* because it wasn't a polished pitch.

---

## Part 2 · The five upgrades

### 1 · Stage‑aware (classify the stage, then score)
Fundraising is a **sequence** of meetings, each with its own bar. *Classify the stage first, then judge against that stage.*

| Stage | The one goal | Reward | Do **not** punish | Realistic conversion |
|---|---|---|---|---|
| **Intro / first (exploratory)** | **Earn the next meeting** + build credibility + surface their real doubt | team credibility, chemistry, a dated next step, reading the room | no formal pitch, no valuation/Series‑A talk, no data‑room ask | ~5–15% advance |
| **Socialization / 2nd** | Get them to sell it internally | a thesis a second person can repeat | — | ~15% |
| **Deep‑dive / product** | Defend data, resolve the core objection | altitude‑shifting, knowing the numbers cold, the right person leading the technical thread | — | ~10% |
| **Partner meeting** | A clean ask + a proposed decision timeline | handling interruptions (= engagement), direct ask, depth under fire | — | 25–60% |
| **Closing** | Terms | term clarity, pacing | — | — |

### 2 · Outcome‑first (the most‑weighted signal)
**"Did a concrete, *dated* next step get set — and who proposed it?"** This is the truest measure of a first meeting and is trackable across recordings.
- Gong (8,382 deals): close rate **5% without** a next step vs **20% with** (4×).
- Paul Graham: *never leave a meeting without asking what happens next.*
- An **investor‑proposed** next step ("send me the deck / let's bring in my partner") ≫ a founder‑proposed one. "Let's stay in touch" = no next step = a soft pass.

### 3 · Objective signals (replace vibes with numbers from the transcript)
Won/lost outcomes are predictable from objective, transcript‑derivable structure (Gong, ~500k calls; Chorus):

| Signal | Read it | Source |
|---|---|---|
| **Founder talk‑ratio** | Healthy ~43–57%; **>65% = pitch dump**. In a first meeting, founder should talk ~⅓. | Gong 43:57 |
| **Longest single monologue** | **>2.5 min = flag** (lost deals have long seller monologues). | Gong |
| **Investor talk / "riffing"** | Investor riffing on "how big this could be" = a strong buy signal. *But volume ≠ warmth* — measure their **behaviors**, not just airtime. | Seibel / a16z |
| **Speaking pace** | Compute chars‑or‑words per second per speaker. Top closers **slow down** when challenged; mid‑performers speed up (a tell). | Gong (173 vs 188 wpm) |
| **Filler vs. hedging** | Filler ("um/uh", crutch words) is **not** correlated with outcomes — don't over‑index on it. **Hedging/qualifiers** ("I think / maybe / sort of / a bit") are credibility leaks — target those. | Gong filler study |
| **Question types (SPIN)** | Reward Implication/Need‑payoff questions over Situation. An investor asking Implication questions is leaning in. | Rackham |
| **Sentiment / topic shifts** | Timestamp where the investor warmed or cooled, and on which topic. | Chorus |

> ⚠️ **Do not fetishize talk‑ratio as a causal lever.** Investor talk‑time is a *correlate* of interest, often reverse‑caused (they talk because they're already interested). You can't manufacture a yes by engineering them to talk. The reason to not monologue is that it lets you read the room, surface objections, and let them self‑persuade — and a 6‑minute monologue is just bad communication. The true ground‑truth is **buyer behaviors** (terms, data‑room, intros, a dated next step), not airtime.

### 4 · Bidirectional (you're interviewing them too)
Add a **mutual‑qualification** dimension most rubrics ignore: did you qualify the investor — thesis fit, value‑add beyond capital, decision process + timeline, check size, source of funds, **founder references**? Then rate the investor **STRONG / MIXED / WEAK** (smart money vs. just capital). Borrow MEDDIC: did you reach the *economic buyer* (the deciding partner, not an associate)? Is there a *champion* who'll sponsor it internally?

### 5 · Team module (multi‑founder choreography)
Tag‑team pitching is a known anti‑pattern (Mirabile/Seraf; Belenzon). Using speaker diarization, score (separately from content):
- **Single narrator** — is one person (the CEO) driving the narrative? Split‑deck = flag.
- **Q&A routing** — does the CEO cleanly hand a domain question to the right co‑founder, who answers *briefly* and hands back?
- **Interruptions / steamrolling / contradictions** — investors read these as "who's in charge / are they aligned." (~65% of startups die from co‑founder conflict; investors weight it heavily.)
- **Talk distribution** — is a key founder (e.g. the domain/FMF anchor) too quiet? is the CEO silent?
- **Stage‑appropriate lineup** — CEO‑solo for a first call; the technical lead leads in a deep‑dive; everyone present at a partner meeting.

### Plus: fairness floor · real gating · regional calibration
- **Temperature by actions, not words:** `COMMITTED‑WARM` (dated next step / terms / data‑room / intro / riffing) > `ENGAGED‑WARM` (deep + warm but no action) > `POLITE‑WARM` (short + nice) > `COLD`.
- **Fairness floor:** if the investor genuinely engaged (long, deep probing, an intro offer) and stated no structural pass, **floor the score ~5.5–6** and note "good relationship signal, conviction pending." Don't invert.
- **Real gating question:** find the *question behind the question* (what they kept circling). Next‑meeting prep targets **that**, not a generic kill‑shot list.
- **Regional calibration:** adapt to your market's norms. (E.g. China/HK fundraising is relationship‑first — don't punish an appropriately "soft" exploratory first meeting; reward direct handling of regulation/CAC; note WeChat‑vs‑email follow‑up. Adjust for your own region.)

---

## Part 3 · Pipeline & output template

```
recording → ① transcribe (+speakers, +timestamps)
          → ② classify TYPE (investor/FA/hybrid/other) × STAGE
          → ③ objective signals + stage scorecard + team module + bidirectional, grounded in pitch-brief.md
          → ④ fixed 11‑section report
          → ⑤ (optional) publish + log
```

The fixed report sections (keep order/titles constant; write "N/A — reason" rather than deleting, so reports diff across meetings): **1 Header (incl. stage) · 2 Verdict (next step? who? · temperature · score w/ fairness floor) · 3 Summary · 4 Objective panel · 5 Stage scorecard · 6 Team dynamics · 7 Mutual‑qualification · 8 Real gating question · 9 Extraction (incl. "what you should have said but didn't") · 10 48h follow‑up draft + role plan · 11 Quotes.**

---

## Part 4 · Customize for your startup

Two pieces of grounding make the report specific instead of generic — fill them in `pitch-brief.md` (copy the template):

1. **Your hardest questions + model answers.** List the 6–10 questions investors actually ask *you*, and what a strong answer must contain. Build this bank from real meetings — after each meeting, add any new question. This is what lets the report say "you fumbled Q3 and never deployed metric X."
2. **Your team ownership map.** For each co‑founder: real background, genuine strengths, **which questions are theirs to field**, and what to check about them. The team module uses this to flag "the CEO should have taken the market question; the CTO over‑answered."

Also note your **known self‑owns** (mistakes you've made before — an over‑broad TAM claim, a contradicted premise) so the report can catch repeats.

---

## Part 5 · Limitations (be honest)
- ASR is lossy on noisy / code‑switched audio; quote *approximately* and flag it. Objective signals (talk‑ratio, monologue length) are robust to small ASR errors.
- Speaker mapping is inferred — confirm "who is who" once per counterparty.
- The rubric encodes *one* point of view; it's a magnifier and a coach, not a judge. Your team makes the call.
- Small‑n: don't over‑read a single meeting; the value compounds across many, compared the same way.

---

## Sources
**Conversation intelligence:** Gong Labs (talk‑to‑listen 43:57; next‑steps 5%→20%; monologue length; filler words ≠ outcome but hedging does; pace 173 vs 188 wpm; pause after objections), Chorus.ai; **qualification:** MEDDIC/MEDDPICC, SPIN (Rackham), BANT, Sandler. **Fundraising:** NextView "The VC Meeting Map", First Round Review (seed partner meeting), Paul Graham "How to Raise Money", Sequoia "How to Present to Investors", Michael Seibel / YC ("be clear, not cool"), a16z (magnitude of strength) / Aaron Harris, Tomasz Tunguz (funnel conversion), Prime Movers Lab "33 questions founders should ask investors". **Multi‑founder:** Mirabile/Seraf "Tag‑Team Pitches Are Terrible", Belenzon "Co‑founders, Stop Pitching Together", CNN "Fighting co‑founders doom startups". **Delivery:** Barbara Minto *Pyramid Principle* (conclusion‑first), Sylvia Ann Hewlett *Executive Presence* (gravitas), HBR/Harvard Extension/Yoodli (filler, uptalk, Think‑Pause‑Speak).
