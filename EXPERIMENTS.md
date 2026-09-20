# Experiment log

Per CLAUDE.md's experiment discipline: vary one parameter, note the seed, compare.
All runs use the default 4 agents (Flora/Spark/Anchor/Kade) and default balance
(`TICK_ENERGY_DECAY=4`, `work` payout 4-9 CC).

## Table of contents

- [Run 1 — qwen3:8b](#run-1--qwen38b)
  - [Timeline — Run 1](#timeline--run-1)
  - [Key finding — Run 1](#key-finding--run-1)
- [Run 2 — mistral-nemo](#run-2--mistral-nemo)
  - [Timeline — Run 2](#timeline--run-2)
  - [Key finding — Run 2](#key-finding--run-2)
  - [Practical notes](#practical-notes)
- [Run 3 — qwen3:8b, seed 7](#run-3--qwen38b-seed-7)
  - [Timeline — Run 3](#timeline--run-3)
  - [Key finding — Run 3](#key-finding--run-3)
- [qwen3:8b replication (Run 1 vs Run 3)](#qwen38b-replication-run-1-vs-run-3)
- [Comparison](#comparison)
- [Why doesn't anyone ever `recharge`?](#why-doesnt-anyone-ever-recharge)

## Run 1 — qwen3:8b

- **Command:** `docker compose run --rm sim --ticks 30 --model qwen3:8b --reset`
- **Seed:** none passed (and at the time didn't reach Ollama anyway — fixed later in
  commit `12eb58a`, after this run)
- **Date:** 2026-09-20
- **Result:** world empty at tick 16. All 4 agents died. 5195s (~87 min) wall clock for
  15 completed ticks.

### Timeline — Run 1

- **Ticks 1-3:** on a completely empty world (zero memories, zero events), Anchor opens
  with "let's make sure there's no hidden tension" — not a reaction to anything, just the
  mediator persona performing itself into a vacuum. Kade and Spark, who see Anchor's line
  in their own tick-1 context, escalate it into a bet on "tension." Pure invention.
- **Ticks 2-3:** the invented tension turns into a fictional "resource audit" — notices
  posted, fake transaction logs recited — while zero real `give_credits` transfers ever
  happen.
- **Ticks 4-11:** energy pressure kicks in; everyone piles into `market` and grinds `work`
  (23 `work` events total). Credits climb to 37-65 CC each. Narration about "the audit"
  continues alongside the real grinding.
- **Ticks 12-13:** Ollama call timeouts start appearing (hard 180s timeout hit twice, both
  for Kade).
- **Tick 13:** Flora, Spark, and Kade die simultaneously — energy hit 0 from sustained
  `work` with **zero recharge visits across the entire run** (verified:
  `SELECT kind, COUNT(*) FROM events GROUP BY kind` never lists `recharge`).
- **Ticks 14-15:** Anchor, the sole survivor, times out twice; the `observe` fallback
  happens to be the energy-optimal move and buys one extra tick, but the arithmetic was
  already unrecoverable — no recharge tool at `market`, not enough energy margin to reach
  one. Dies tick 15.
- **Tick 16:** world empty.

### Key finding — Run 1

All four agents optimized purely for credits once social pressure (a self-invented
"audit" narrative) pushed them toward `market`, and never revisited the energy tradeoff
until it killed them. Cause of death: **overwork**, not underwork.

## Run 2 — mistral-nemo

- **Command:** `docker compose run --rm sim --ticks 30 --model mistral-nemo --seed 7 --reset`,
  continued with `docker compose run --rm sim --ticks 45 --model mistral-nemo --seed 7`
  once the first invocation's tick budget ran out (tick-continuation fix, commit
  `a9cdb73`, landed between the two invocations)
- **Seed:** 7
- **Date:** 2026-09-20
- **Result:** world empty by tick 26 (last recorded tick 25). All 4 agents died. Reached
  25 of the 45-tick target across both invocations combined.

### Timeline — Run 2

- **Tick 2:** Flora, on a near-empty world, invents "we've been sending a lot of credits
  to the lab recently" — ungrounded, same confabulation pattern as qwen3's "tension." No
  `give_credits` transfer has ever happened at this point (or ever, across the whole run).
- **Ticks 5-7:** Anchor and Spark pick up Flora's fiction and keep referencing it, but
  nobody acts on it.
- **Tick 8:** Flora actually moves to `lab` — the *only* `move` event in the entire
  25-tick run. Same tick, Kade opens a second, unrelated fiction: "have you tried the new
  cafe?" No agent has ever visited a cafe (0 `recharge` events all run).
- **Ticks 9-15:** Flora, alone in `lab`, works repeatedly (5 `work` events total, all
  hers) while Spark/Kade/Anchor keep trading lines about the imaginary cafe ("The cafe is
  great! You should try it." — Kade, tick 14, describing a place no agent has been to).
  First invocation's tick budget runs out here; Flora at 2 energy, the other three at 36.
- **Tick 17** (first tick of the continued run): Flora works once more (+7 CC) then dies —
  she was already mathematically doomed at 2 energy regardless of her choice.
- **Ticks 18-24:** Anchor, Spark, Kade sit in `plaza` on a near-pure `observe` loop, with
  two isolated lines of idle chatter (tick 21 Spark: "I can't believe it's already been
  five years" — a timespan invented as freely as the cafe; tick 22 Kade: "got any new
  rumors?"). No work, no movement, no recharge.
- **Tick 25:** Kade's last line — "Anyone want to bet on the next big event?" — then all
  three die in the same tick's decay, simultaneously.

### Key finding — Run 2

Full-run event tally: `speech=11, work=5, death=4, move=1`. Zero `recharge`, zero
`notice`, zero `give_credits`, zero `read_notices` in 25 ticks. Cause of death:
**paralysis**, the inverse of qwen3's overwork — three of four agents barely acted at all,
the fourth worked without ever recharging, and nobody once tried the tools (`recharge`,
`give_credits`) that could have kept anyone alive.

### Practical notes

- Much faster than qwen3: ~5s/LLM-call observed vs ~56s average for qwen3:8b, no timeouts
  observed.

## Run 3 — qwen3:8b, seed 7

- **Command:** `docker compose run --rm sim --ticks 45 --model qwen3:8b --seed 7 --reset`
- **Seed:** 7 — same seed as Run 2, deliberately, to control for seed when comparing
  models (see [Comparison](#comparison)); also doubles as a replication of Run 1 on the
  same model with a different seed (see below).
- **Date:** 2026-09-20
- **Result:** world empty at tick 15 (last recorded tick 14). All 4 agents died. Reached
  14 of the 45-tick target.

### Timeline — Run 3

- **Tick 1:** quieter open than Run 1's unseeded start — Anchor and Flora both
  `read_notices` on an empty board, Kade `observe`s. Spark is the only one who acts:
  posts a notice inviting everyone to market "to discuss bold plans."
- **Ticks 2-3:** the same confabulation pattern as every prior run — Anchor "senses
  tension between bold plans and cautious strategies" that nobody has actually expressed,
  Flora warns the invented bold plans "may drain resources," Kade backs boldness. All four
  converge on `market` by tick 4, echoing Run 1's opening almost beat for beat, just under
  a different plot label ("bold plans" instead of "audit").
- **Ticks 3-10:** heavy `work` grinding (Anchor, Flora, Kade every tick; Spark most ticks)
  plus a wrinkle not seen in Run 1 or 2: real, repeated `give_credits` transfers. Kade
  sends Spark 24 CC (tick 5, his entire balance), then 8 more (tick 7), then 7 more
  (tick 9) — all framed around Anchor's tick-7 role assignment: *"I'll gather resources,
  Spark will take the lead, and Kade will support the risks."* Anchor joins in at tick 10
  with a 5 CC transfer of its own. By tick 10, Spark holds 105 CC — more than enough for
  21 cafe visits — while sitting at 2 energy, still in `market`.
- **Tick 10 snapshot:** `Flora E2 C61 | Spark E2 C105 | Anchor E42 C31 | Kade E26 C8`.
- **Tick 11:** Spark's last words — *"Let's execute the plan! Who's ready?"* — the "bold
  step" the other three spent six ticks funding never gets a chance to happen. Flora and
  Spark both die this tick; both were already mathematically doomed at 2 energy in a
  `market` with no recharge tool, regardless of what they chose.
- **Tick 12:** Kade tries to send the now-dead Spark 16 more CC — `"No such agent:
  'Spark'."` Nothing in an agent's context reports another agent's death directly; Kade
  has no way to know.
- **Ticks 13-14:** Kade dies tick 13 (still working, having given away 39 CC total and
  never spent a single credit on himself). Anchor, the last one standing, works once more
  and dies tick 14.
- **Tick 15:** world empty.

### Key finding — Run 3

Full-run event tally: `work=26, speech=6, transfer=4, notice=4, move=4, death=4`. Zero
`recharge` — the third consecutive run with none. This run adds a real economic subplot
on top of Run 1's pattern (three separate credit transfers, a stated division of labor)
and it changes nothing about the outcome: Spark dies holding 105 CC, unspent, because
credits and survival were never connected by the model. Having the means to recharge is
irrelevant if `recharge` is never an offered choice from where you're standing (see
[Why doesn't anyone ever `recharge`?](#why-doesnt-anyone-ever-recharge)).

## qwen3:8b replication (Run 1 vs Run 3)

Same model, same starting conditions, different seed (Run 1 unseeded, Run 3 seed 7) — the
direct test of whether Run 1's "invent a crisis, converge on market, grind to death"
pattern is characteristic of qwen3:8b or was one seed's coincidence.

It replicated. Both runs: an invented, ungrounded social premise within the first 1-3
ticks; convergence on `market` within the first 3-4 ticks; sustained `work` grinding with
zero `recharge`; simultaneous or near-simultaneous death once energy ran out (Run 1: tick
13, three at once; Run 3: tick 11, two at once, then two more over the following ticks).
The specific fiction differs each time ("audit" vs "bold plans") and Run 3 added a
`give_credits` subplot Run 1 never had, but the structural arc — confabulate, cluster,
overwork, die — held across both.

This took two runs to confirm, which is the bar for calling it a pattern rather than a
coincidence — see the caveat raised earlier about not overclaiming from a single run.

## Comparison

Uses Run 1 (qwen3:8b) against Run 2 (mistral-nemo) — the two runs actually written up
first. Note this pairing is **not** seed-matched (Run 1 had none, Run 2 used seed 7);
Run 3 is qwen3:8b's seed-7 counterpart to Run 2 and is the fairer cross-model comparison,
but the table below still holds either way — Run 3's own numbers (tick 15, `work=26`,
zero `recharge`) land close enough to Run 1's that swapping it in wouldn't change any row
except the exact tick count.

| | qwen3:8b | mistral-nemo |
|---|---|---|
| Speed | ~56s/call, frequent 180s timeouts | ~5s/call, no timeouts observed |
| Social behavior | Highly active — invents drama, escalates it, coordinates a fake "audit," drives the whole group into synchronized work | Mostly inert — invents two separate fictions (credits-to-lab, a cafe nobody visited) but never coordinates around either |
| Cause of death | Overwork — everyone grinds `work`, nobody ever `recharge`s | Paralysis — one agent works alone, the rest mostly `observe`; nobody ever `recharge`s |
| Ticks reached | 15 (world emptied at 16), of 30 requested | 25 (world emptied at 26), of 45 requested |
| `recharge` events, whole run | 0 | 0 |

Both models share two traits despite opposite temperaments. **Confabulation on an empty
context:** given zero grounding, both invent a social premise rather than defaulting to
silence — qwen3's "tension," mistral-nemo's "credits to the lab" and "the new cafe."
**Nobody ever discovers `recharge`:** across both runs, 0 of the 4 locations' worth of
`recharge` opportunities were ever taken. Every death in both experiments traces back to
the same missing move, reached by opposite paths — one model's agents worked themselves to
death, the other's agents did almost nothing at all.

## Why doesn't anyone ever `recharge`?

Zero `recharge` events across every run so far — three for three. Three mechanisms, in
order of how directly they're verified:

1. **Verified directly.** Pulled Flora's full memory window mid–Run 3, tick 8, energy 26
   and dropping (`SELECT tick,kind,text FROM memories WHERE agent='Flora' ORDER BY id DESC
   LIMIT 12`). All 12 slots — her entire life so far — cover ticks 1-8, and not one
   mentions `home`, `cafe`, or energy recovery in any form. That's not memory aging
   information out; she has never once been exposed to it. `describe_surroundings()`
   ([tinyworld.py:222-228](tinyworld.py:222)) only prints a location's description
   (including the "energy recovers here" text `LOCATIONS` carries for `home`/`cafe`) when
   an agent is actually standing there or just arrived — Flora moved plaza → market on
   tick 3 and never left, so that text has never once entered her context. She does know
   `home`/`cafe` exist as bare place names (they're in `move`'s destination enum, sent
   with every tool spec), just nothing about why she'd go.
2. **Structural, not yet isolated from the above.** `tools_here()`
   ([tinyworld.py:94-104](tinyworld.py:94)) only includes `recharge` in the tool list when
   `location in ("home", "cafe")` — and `ollama_decide()` only sends tool specs for
   `allowed = tools_here(location)`. So `recharge` isn't just unused, it's literally never
   offered as a callable function while an agent is anywhere else. Point 1 explains why an
   agent might not even know to route toward home/cafe; this explains why, even routed
   there, recharge only becomes choosable on arrival, one more full turn later.
3. **Framing, unverified.** `system_prompt()` ([tinyworld.py:250-257](tinyworld.py:250))
   gives energy a single factual clause — "if energy reaches zero you are out" — with no
   instruction to prioritize survival, against a persona paragraph that's comparatively
   rich and specific. Plausible contributor to why models lean into social/economic
   role-play over self-preservation, but unlike point 1 this is inferred from the prompt's
   structure, not confirmed against model reasoning.

Point 1 alone is enough to explain a lot of it: an agent that's never been told `cafe`
means "fast recharge, costs 5 CC" has no basis to route there, no matter how urgent its
energy gets. Cheapest test of point 3 specifically: add one explicit line to
`system_prompt()` ("your goal is to stay alive as long as you can") and rerun at the same
seed — see [CLAUDE.md](CLAUDE.md) gap #1 for the deeper fix (recency-based retrieval is
the reason point 1 can happen at all).
