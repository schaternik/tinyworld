# tinyworld

A minimal agent-society simulation in the spirit of Emergence World
(<https://github.com/EmergenceAI/Emergence-World> — docs and data only, engine is closed source).
Autonomous LLM agents live in a small world, act only through tools, and burn energy
to stay alive. The point is to observe what emerges, not to complete a task.

## Stack

- Python 3.12, stdlib only. No dependencies, deliberately.
- SQLite for all world state (`/data/world.db` in Docker, `./world.db` locally).
- Ollama for inference via `POST /api/chat` with tool calling.
- Docker for the sim container; Ollama runs natively on the host.

## Files

- `tinyworld.py` — the whole simulation: world, tools, context assembly, main loop.
- `Dockerfile` / `docker-compose.yml` — sim container; `bundled` profile also runs Ollama
  in a container (Linux/NVIDIA only — no Metal passthrough on macOS).

## Running

```bash
python tinyworld.py --ticks 40 --model mock --seed 3 --reset   # dry run, no LLM
python tinyworld.py --ticks 30 --model qwen3:8b --reset        # local Ollama
docker compose run --rm sim --ticks 30 --model qwen3:8b --reset
```

`--model mock` swaps the LLM for a dumb heuristic. Use it for every change to world
mechanics, balance, or schema — it runs in milliseconds and keeps the GPU out of the loop.

## Design constraints — do not break these

1. **Agents act only through tools.** No free-text output may mutate world state.
   `execute()` is the single write path into the world.
2. **Tools are gated by location.** `tools_here()` is the primary design lever; changing
   what is available where is how you change the society.
3. **Scarcity drives the loop.** Energy decays every tick. Remove the pressure and agents
   stop having reasons to do anything.
4. **Everything is logged.** Every action writes to `events`; agent-visible facts write to
   `memories`. A run you cannot reconstruct from SQLite is a run that taught you nothing.
5. **Keep it dependency-free** unless there is a real reason. `sqlite-vec` is the one
   expected exception.

## Known gaps, roughly in priority order

1. **Memory retrieval is naive.** `build_context()` takes the last 12 memories by recency.
   This is the main reason agents look forgetful. Replace with `sqlite-vec` embeddings plus
   an importance score, per the Generative Agents recipe (recency × relevance × importance).
2. **No reflection.** Add a periodic extra LLM call — "what have you concluded about the
   other agents and this world" — writing results back as `kind='reflection'` memories.
   This is what turns a sequence of actions into something resembling character.
3. **No governance.** Add `propose` / `vote` tools, store the constitution in the `meta`
   table, and inject it into the system prompt. This is the actually interesting part.
4. **No replay.** Raw model responses are not stored, so runs are not reproducible even
   though `--seed` now also seeds each Ollama call (drawn from the same seeded stream as
   work payouts). A fixed seed reproduces the sampling; it does not reproduce a run, since
   nothing captures what Ollama actually returned. Log raw responses to a new table and add
   `--replay` if reproducibility is needed.
5. **No destructive tools.** `steal`, `arson` etc. Add last and deliberately: they produce
   drama at the cost of interpretability.
6. **No frontend.** Read the world with `sqlite3`. A websocket feed or 2D grid is optional
   polish and should not be prioritised over 1–3.

## Model notes

Tool-calling reliability matters far more than model size here. Qwen3 and Mistral-Nemo
are reliable; many similarly sized models return empty content or malformed arguments.
A log full of `observe` usually means failed tool calls, not thoughtful agents.

World content and prompts are in English on purpose — smaller models call tools more
reliably in English.

## Experiment discipline

This is a lab, not a story generator. Vary exactly one parameter between runs and fix
`--seed`. The interesting knobs: `TICK_ENERGY_DECAY` (scarcity), `work` payout range
(inequality), and presence of enforcement once destructive tools exist. Two runs on the
same seed differing in one variable is a result; "I ran it and things happened" is not.
