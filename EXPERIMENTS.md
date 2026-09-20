# Experiment log

Per CLAUDE.md's experiment discipline: vary one parameter, note the seed, compare.
All runs use the default 4 agents (Flora/Spark/Anchor/Kade) and default balance
(`TICK_ENERGY_DECAY=4`, `work` payout 4-9 CC).

## Run 1 — qwen3:8b

- **Command:** `docker compose run --rm sim --ticks 30 --model qwen3:8b --reset`
- **Seed:** none passed (and at the time didn't reach Ollama anyway — fixed later in
  commit `12eb58a`, after this run)
- **Date:** 2026-09-20
- **Result:** world empty at tick 16. All 4 agents died. 5195s (~87 min) wall clock for
  15 completed ticks.

### Timeline

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

### Key finding

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

### Timeline

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

### Key finding

Full-run event tally: `speech=11, work=5, death=4, move=1`. Zero `recharge`, zero
`notice`, zero `give_credits`, zero `read_notices` in 25 ticks. Cause of death:
**paralysis**, the inverse of qwen3's overwork — three of four agents barely acted at all,
the fourth worked without ever recharging, and nobody once tried the tools (`recharge`,
`give_credits`) that could have kept anyone alive.

### Practical notes

- Much faster than qwen3: ~5s/LLM-call observed vs ~56s average for qwen3:8b, no timeouts
  observed.

## Comparison

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
