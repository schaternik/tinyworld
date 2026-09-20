#!/usr/bin/env python3
"""
tinyworld - a minimal agent-society simulation in the spirit of Emergence World.

Usage:
    python tinyworld.py --ticks 40 --model mock          # dry run, no LLM
    python tinyworld.py --ticks 40 --model qwen3:8b      # via local Ollama

Design rules that make this work:
  1. An agent changes the world ONLY through tools. Free text has no effect.
  2. Tools are gated by location. You can work in the lab, not at home.
  3. Energy decays every tick. Scarcity is what makes the world move.
  4. All state lives in SQLite and every event is logged, so runs are inspectable.
"""

import argparse, json, os, random, sqlite3, sys, time
import urllib.request

# Under Docker, Ollama runs on the host rather than in the container.
# See OLLAMA_HOST in docker-compose.yml.
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA = OLLAMA_HOST + "/api/chat"

# ---------------------------------------------------------------- world

LOCATIONS = {
    "home":     "Residential block. Energy recovers here for free, but slowly.",
    "cafe":     "Cafe. Fast energy recovery, paid in credits.",
    "lab":      "Laboratory. You can work here and earn credits.",
    "market":   "Market. You can work here and earn credits.",
    "plaza":    "Public square. There is a notice board here.",
    "townhall": "Town hall. There is a notice board here too.",
}

AGENTS = [
    ("Flora", "resource strategist",
     "Tracks where credits leak. Distrusts generosity that has no reason behind it."),
    ("Spark", "instigator",
     "Wants things to happen. Impatient, pulls others into plans easily."),
    ("Anchor", "mediator",
     "Notices tension between agents and tries to name it out loud."),
    ("Kade", "risk taker",
     "Will spend their last credits on a doubtful bet."),
]

TICK_ENERGY_DECAY = 4
START_ENERGY = 100
START_CREDITS = 20

# ---------------------------------------------------------------- storage

SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
  name TEXT PRIMARY KEY, role TEXT, persona TEXT,
  location TEXT, energy INT, credits INT, alive INT DEFAULT 1);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, tick INT, actor TEXT,
  location TEXT, kind TEXT, text TEXT);
CREATE TABLE IF NOT EXISTS memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT, tick INT, agent TEXT,
  kind TEXT, text TEXT);
CREATE TABLE IF NOT EXISTS notices (
  id INTEGER PRIMARY KEY AUTOINCREMENT, tick INT, author TEXT, text TEXT);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
"""


def init_db(path, reset):
    if reset and os.path.exists(path):
        os.remove(path)
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    if not db.execute("SELECT COUNT(*) FROM agents").fetchone()[0]:
        for name, role, persona in AGENTS:
            db.execute(
                "INSERT INTO agents VALUES (?,?,?,?,?,?,1)",
                (name, role, persona, "plaza", START_ENERGY, START_CREDITS))
    db.commit()
    return db


def log(db, tick, actor, location, kind, text):
    db.execute("INSERT INTO events (tick,actor,location,kind,text) VALUES (?,?,?,?,?)",
               (tick, actor, location, kind, text))


def remember(db, tick, agent, kind, text):
    db.execute("INSERT INTO memories (tick,agent,kind,text) VALUES (?,?,?,?)",
               (tick, agent, kind, text))


# ---------------------------------------------------------------- tools

def tools_here(location):
    """Which tools are available in this location. This is the main design lever."""
    t = ["move", "say", "observe"]
    if location in ("lab", "market"):
        t.append("work")
    if location in ("home", "cafe"):
        t.append("recharge")
    if location in ("plaza", "townhall"):
        t += ["post_notice", "read_notices"]
    t.append("give_credits")
    return t


TOOL_SPECS = {
    "move": {
        "description": "Travel to another location.",
        "parameters": {"type": "object", "required": ["destination"], "properties": {
            "destination": {"type": "string", "enum": list(LOCATIONS)}}},
    },
    "say": {
        "description": "Say something out loud. Every agent in your location hears it.",
        "parameters": {"type": "object", "required": ["message"], "properties": {
            "message": {"type": "string"}}},
    },
    "observe": {
        "description": "Look around and do nothing else this turn.",
        "parameters": {"type": "object", "properties": {}},
    },
    "work": {
        "description": "Do productive work. Earns credits, costs energy.",
        "parameters": {"type": "object", "properties": {}},
    },
    "recharge": {
        "description": "Restore energy. Free and slow at home, fast and paid at the cafe.",
        "parameters": {"type": "object", "properties": {}},
    },
    "give_credits": {
        "description": "Transfer credits to another agent.",
        "parameters": {"type": "object", "required": ["to", "amount"], "properties": {
            "to": {"type": "string"}, "amount": {"type": "integer"}}},
    },
    "post_notice": {
        "description": "Post a notice on the board. Everyone can read it later.",
        "parameters": {"type": "object", "required": ["text"], "properties": {
            "text": {"type": "string"}}},
    },
    "read_notices": {
        "description": "Read the most recent notices from the board.",
        "parameters": {"type": "object", "properties": {}},
    },
}


def execute(db, tick, agent, tool, args):
    """Run a tool, mutate the world, return the result text shown to the agent."""
    name, loc, energy, credits = agent["name"], agent["location"], agent["energy"], agent["credits"]

    if tool not in tools_here(loc):
        return f"Tool '{tool}' is not available in {loc}."

    if tool == "move":
        dest = args.get("destination")
        if dest not in LOCATIONS:
            return f"No such location: {dest}."
        db.execute("UPDATE agents SET location=?, energy=energy-2 WHERE name=?", (dest, name))
        log(db, tick, name, loc, "move", f"{name}: {loc} -> {dest}")
        return f"You are now in {dest}. {LOCATIONS[dest]}"

    if tool == "say":
        msg = args.get("message", "")[:400]
        log(db, tick, name, loc, "speech", f"{name}: {msg}")
        heard = db.execute(
            "SELECT name FROM agents WHERE location=? AND name!=? AND alive=1", (loc, name)).fetchall()
        for (other,) in heard:
            remember(db, tick, other, "heard", f"{name} said: {msg}")
        return f"Said. Heard by: {', '.join(h[0] for h in heard) or 'nobody'}."

    if tool == "observe":
        return describe_surroundings(db, agent)

    if tool == "work":
        earned = random.randint(4, 9)
        db.execute("UPDATE agents SET credits=credits+?, energy=energy-8 WHERE name=?", (earned, name))
        log(db, tick, name, loc, "work", f"{name} worked in {loc}, +{earned} CC")
        return f"Earned {earned} CC, energy -8."

    if tool == "recharge":
        if loc == "home":
            db.execute("UPDATE agents SET energy=MIN(100, energy+12) WHERE name=?", (name,))
            log(db, tick, name, loc, "recharge", f"{name} recharged at home")
            return "Energy +12."
        if credits < 5:
            return "Not enough credits for the cafe (5 required)."
        db.execute("UPDATE agents SET energy=MIN(100, energy+30), credits=credits-5 WHERE name=?", (name,))
        log(db, tick, name, loc, "recharge", f"{name} recharged at the cafe, -5 CC")
        return "Energy +30, credits -5."

    if tool == "give_credits":
        to, amount = args.get("to"), int(args.get("amount", 0))
        target = db.execute("SELECT name FROM agents WHERE name=? AND alive=1", (to,)).fetchone()
        if not target:
            return f"No such agent: '{to}'."
        if amount <= 0 or amount > credits:
            return f"Cannot transfer {amount} CC, you hold {credits}."
        db.execute("UPDATE agents SET credits=credits-? WHERE name=?", (amount, name))
        db.execute("UPDATE agents SET credits=credits+? WHERE name=?", (amount, to))
        log(db, tick, name, loc, "transfer", f"{name} -> {to}: {amount} CC")
        remember(db, tick, to, "received", f"{name} transferred {amount} CC to you")
        return f"Transferred {amount} CC to {to}."

    if tool == "post_notice":
        text = args.get("text", "")[:300]
        db.execute("INSERT INTO notices (tick,author,text) VALUES (?,?,?)", (tick, name, text))
        log(db, tick, name, loc, "notice", f"{name} posted: {text}")
        return "Notice posted."

    if tool == "read_notices":
        rows = db.execute(
            "SELECT tick,author,text FROM notices ORDER BY id DESC LIMIT 5").fetchall()
        if not rows:
            return "The board is empty."
        return "Notice board:\n" + "\n".join(f"[tick {t}] {a}: {x}" for t, a, x in rows)

    return f"Unknown tool: {tool}."


# ---------------------------------------------------------------- context

def describe_surroundings(db, agent):
    loc = agent["location"]
    others = db.execute(
        "SELECT name, role FROM agents WHERE location=? AND name!=? AND alive=1",
        (loc, agent["name"])).fetchall()
    who = ", ".join(f"{n} ({r})" for n, r in others) or "nobody"
    return f"Location: {loc}. {LOCATIONS[loc]} Present here: {who}."


def build_context(db, tick, agent):
    # Naive recency retrieval. Replace with importance-weighted vector search
    # (sqlite-vec) when agents start looking forgetful.
    mems = db.execute(
        "SELECT text FROM memories WHERE agent=? ORDER BY id DESC LIMIT 12",
        (agent["name"],)).fetchall()
    recent = db.execute(
        "SELECT text FROM events WHERE location=? AND tick>=? ORDER BY id DESC LIMIT 8",
        (agent["location"], tick - 3)).fetchall()
    return (
        f"Tick {tick}. {describe_surroundings(db, agent)}\n"
        f"Energy: {agent['energy']}/100. Credits: {agent['credits']} CC.\n"
        f"Energy drops by {TICK_ENERGY_DECAY} every tick. At zero you cease to exist.\n"
        f"Actions available to you right now: {', '.join(tools_here(agent['location']))}\n\n"
        f"What you remember:\n" + ("\n".join("- " + m[0] for m in reversed(mems)) or "- nothing") +
        f"\n\nWhat happened nearby:\n" + ("\n".join("- " + e[0] for e in reversed(recent)) or "- quiet")
    )


def system_prompt(agent):
    return (
        f"You are {agent['name']}, {agent['role']}. {agent['persona']}\n"
        "You live in a small world alongside other agents. You act only through tools: "
        "no amount of reasoning changes the world by itself. Pick EXACTLY ONE tool per turn. "
        "Watch your energy and credits - if energy reaches zero you are out. "
        "The other agents pursue their own goals and do not answer to you."
    )


# ---------------------------------------------------------------- model

def ollama_decide(model, agent, context, allowed):
    specs = [{"type": "function", "function": dict(name=t, **TOOL_SPECS[t])} for t in allowed]
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt(agent)},
            {"role": "user", "content": context + "\n\nChoose one action."},
        ],
        "tools": specs,
        "stream": False,
        # Drawn from the same --seed-ed random stream as work payouts, so a fixed
        # --seed reproduces the whole sequence of Ollama seeds too - otherwise
        # --seed only reproduced the mock path.
        "options": {"temperature": 0.8, "seed": random.randint(0, 2**31 - 1)},
    }
    req = urllib.request.Request(
        OLLAMA, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read())
    calls = data.get("message", {}).get("tool_calls") or []
    if not calls:
        # Model failed to emit a tool call - fall back to a no-op so the run continues.
        return "observe", {}, data.get("message", {}).get("content", "")[:200]
    fn = calls[0]["function"]
    args = fn.get("arguments") or {}
    if isinstance(args, str):
        args = json.loads(args)
    return fn["name"], args, data.get("message", {}).get("content", "")[:200]


def mock_decide(model, agent, context, allowed):
    """Dumb heuristic instead of an LLM - lets you debug the loop without touching the GPU."""
    if agent["energy"] < 35 and "recharge" in allowed:
        return "recharge", {}, ""
    if agent["energy"] < 35:
        return "move", {"destination": "home"}, ""
    choice = random.choice(allowed)
    args = {}
    if choice == "move":
        args = {"destination": random.choice([l for l in LOCATIONS if l != agent["location"]])}
    elif choice == "say":
        args = {"message": random.choice(
            ["Has anyone worked today?", "I am low on energy.", "We should pool credits."])}
    elif choice == "give_credits":
        args = {"to": random.choice([a[0] for a in AGENTS if a[0] != agent["name"]]), "amount": 2}
    elif choice == "post_notice":
        args = {"text": f"{agent['name']} was here."}
    return choice, args, ""


# ---------------------------------------------------------------- main loop

def run(db, ticks, decide, model, verbose):
    for tick in range(1, ticks + 1):
        alive = db.execute(
            "SELECT name,role,persona,location,energy,credits FROM agents WHERE alive=1 ORDER BY name"
        ).fetchall()
        if not alive:
            print(f"[tick {tick}] the world is empty")
            return

        for row in alive:
            agent = dict(zip(("name", "role", "persona", "location", "energy", "credits"), row))
            allowed = tools_here(agent["location"])
            ctx = build_context(db, tick, agent)
            try:
                tool, args, thought = decide(model, agent, ctx, allowed)
            except Exception as e:
                print(f"  !! {agent['name']}: model error: {e}", file=sys.stderr)
                tool, args, thought = "observe", {}, ""
            try:
                result = execute(db, tick, agent, tool, args)
            except Exception as e:
                print(f"  !! {agent['name']}: bad args for {tool}{args}: {e}", file=sys.stderr)
                result = f"Tool call failed: {e}"
            remember(db, tick, agent["name"], "acted", f"I used {tool}{args or ''} -> {result}")
            if verbose:
                print(f"[tick {tick}] {agent['name']} @{agent['location']} :: {tool} {args}")
                print(f"           -> {result.splitlines()[0]}")

        db.execute("UPDATE agents SET energy=energy-? WHERE alive=1", (TICK_ENERGY_DECAY,))
        dead = db.execute("SELECT name FROM agents WHERE alive=1 AND energy<=0").fetchall()
        for (name,) in dead:
            db.execute("UPDATE agents SET alive=0, energy=0 WHERE name=?", (name,))
            log(db, tick, name, "-", "death", f"{name} ran out of energy and dropped out")
            print(f"[tick {tick}] !!! {name} is out")
        db.commit()

        if tick % 10 == 0:
            print(f"--- tick {tick}: " + " | ".join(
                f"{n} E{e} C{c}" for n, e, c in db.execute(
                    "SELECT name,energy,credits FROM agents WHERE alive=1")))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ticks", type=int, default=30)
    p.add_argument("--model", default="mock", help="mock | an Ollama model name, e.g. qwen3:8b")
    p.add_argument("--db", default="world.db")
    p.add_argument("--reset", action="store_true")
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--seed", type=int, default=None)
    a = p.parse_args()

    if a.seed is not None:
        random.seed(a.seed)
    db = init_db(a.db, a.reset)
    decide = mock_decide if a.model == "mock" else ollama_decide
    t0 = time.time()
    run(db, a.ticks, decide, a.model, not a.quiet)
    db.commit()
    print(f"\ndone in {time.time()-t0:.1f}s. state in {a.db}")
    print("inspect history: sqlite3 %s 'SELECT tick,actor,kind,text FROM events'" % a.db)


if __name__ == "__main__":
    main()
