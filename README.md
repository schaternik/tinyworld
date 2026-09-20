# tinyworld

A minimal agent-society simulation in the spirit of [Emergence World](https://world.emergence.ai/season-1)
(docs and data only — the engine itself is closed source). A handful of autonomous LLM
agents live in a small world, act only through tools, and burn energy to stay alive. The
point is to watch what emerges, not to complete a task.

Python 3.12, stdlib only, SQLite for all state. No frameworks, no vector DB (yet), no
cloud API — inference runs locally through [Ollama](https://ollama.com).

## How it works

Four agents (Flora, Spark, Anchor, Kade — each with a one-line persona) start in a plaza
with 100 energy and 20 credits. Every tick, each living agent gets one tool call: `move`,
`say`, `work`, `recharge`, `give_credits`, `post_notice`, `read_notices`, or `observe`.
Which tools are available depends on where they are — you can work in the lab, not at
home. Energy drains every tick regardless of what an agent does; hit zero and you're out.
Every action is logged to SQLite, so a run is fully reconstructable after the fact.

That's the entire mechanic. There's no plot, no goals beyond staying alive, no
scripted events — whatever happens, happens because the model decided it should.

## Quick start

```bash
# dry run, no LLM - deterministic heuristic instead of a model
python tinyworld.py --ticks 40 --model mock --seed 3 --reset

# via local Ollama (pull the model first: ollama pull qwen3:8b)
python tinyworld.py --ticks 30 --model qwen3:8b --reset

# or in Docker, with Ollama running natively on the host
docker compose run --rm sim --ticks 30 --model qwen3:8b --reset
```

Inspect any run directly with `sqlite3`:

```bash
sqlite3 world.db 'SELECT tick, actor, kind, text FROM events ORDER BY id'
```

`--model mock` swaps the LLM for a dumb heuristic — use it for anything touching world
mechanics or balance, since it runs in milliseconds and needs no GPU.

## What comes out of it

Two full runs so far (qwen3:8b and mistral-nemo, same starting conditions) both ended in
every agent dying — and both died for the identical underlying reason: nobody ever used
`recharge`, not once, in either run. They just got there by opposite paths — one model
grouped up and worked itself to death chasing credits it invented a reason to chase;
the other mostly sat in place doing nothing until decay caught up. Full write-up in
[EXPERIMENTS.md](EXPERIMENTS.md).

## Design constraints

1. **Agents act only through tools.** No free-text output mutates world state.
2. **Tools are gated by location.** Changing what's available where is how you change
   the society.
3. **Scarcity drives the loop.** Energy decays every tick — remove that and agents have
   no reason to do anything.
4. **Everything is logged.** A run you can't reconstruct from SQLite taught you nothing.
5. **Dependency-free unless there's a real reason.**

## Status

Working but early. No memory retrieval beyond recency, no reflection, no governance, no
replay, no destructive tools, no frontend — see [CLAUDE.md](CLAUDE.md) for the full,
prioritized list of what's missing and why.

## License

[MIT](LICENSE)
