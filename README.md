# Agent Tape 📼

## The problem

One Tuesday afternoon, a teammate slacked me: *"the agent did the wrong thing on case #4839, can you look?"* I opened our logs. They were a 12 MB jumble of stdout from four services, no consistent format, no causality between the LLM call and the SQL it eventually ran. Two hours later I still didn't know what the model had seen at step three.

This happens every week. Agents are stochastic, multi-step, and they ride on top of side-effectful tools. Reproducing a real incident without good traces is closer to forensics than debugging.

## Our approach

Treat every "thing that happened in an agent run" as a typed event with a monotonic id, a wall-clock timestamp, and a JSON payload. Append-only. JSONL on disk. That's the entire data model.

Once you have that, the things you want fall out naturally:

- A **timeline view** is just iterating the file.
- A **replay** is a lookup: given `(tool_name, arguments)`, return the recorded result instead of actually calling the tool. The agent thinks it's still talking to the real world; you can swap the model.
- **Diffs** between runs work because event ids are monotonic.
- **Aggregation** over runs is just `wc` and `jq`.

## Show me

```python
from tape import Recorder

with Recorder("tapes/today.jsonl") as rec:
    rec.user_msg("How much for 3 apples?")

    with rec.tool("get_price", {"fruit": "apple"}) as s:
        s.set_result(5.0)

    rec.assistant_msg("That's 15 yuan.")
```

The file ends up looking like:

```
{"id":1,"type":"session_start","ts":1715512382.21,...}
{"id":2,"type":"user_msg","payload":{"content":"How much for 3 apples?"},...}
{"id":3,"type":"tool_call_start","payload":{"name":"get_price","arguments":{"fruit":"apple"}},...}
{"id":4,"type":"tool_call_end","parent_id":3,"elapsed_ms":12.4,"payload":{"name":"get_price","ok":true,"result":5.0}}
{"id":5,"type":"assistant_msg","payload":{"content":"That's 15 yuan."},...}
{"id":6,"type":"session_end",...}
```

Pretty-print it with the bundled viewer:

```bash
python -m tape.view tapes/today.jsonl
```

You get a colored, indented timeline. No web UI, no database, nothing to install.

## Replay

This is the part that earned the repo its name. Suppose you want to see how a different model would have answered, given the *same* tool outputs. You don't want to hit the real APIs again — they're slow, costly, and possibly non-deterministic.

```python
from tape import Replay

tape = Replay("tapes/today.jsonl")

# ... in your agent loop, wherever you'd call the real tool:
result = tape.call("get_price", {"fruit": "apple"})   # returns 5.0
```

If a tool call wasn't recorded, `tape.call` raises `KeyError`. That's intentional — it makes silent drift between recording and replay impossible.

## Getting started

```bash
git clone https://github.com/sitianjia/agent-tape
cd agent-tape
pip install -e .
pytest -q
```

There's no daemon and no service. The recorder is a single Python class. You can use it from any agent framework — LangChain, LlamaIndex, a hand-rolled loop, whatever.

## How it works

```
your code        recorder            disk                 replay
─────────        ──────────          ───────────────      ──────────────
rec.user_msg()────▶ Event(id=1) ────▶ jsonl line ────▶ JSONLStream ───▶
with rec.tool():──▶ Event(id=2, "start")
  ...            ▶ Event(id=3, "end", parent_id=2)
                                                            │
                                                            ▼
                                                       Replay.call(name, args)
                                                            │
                                                            ▼
                                                       cached result
```

The Recorder is thread-safe (one lock around the file write). It flushes after every event by default — change `flush_every` if you're recording millions per second.

Spans (`with rec.tool(...) as s`) automatically pair start and end events. If your code raises inside the span, the end event records the exception. You don't have to remember to do anything.

## What this is not

- **Not a metrics system.** Use Prometheus or whatever for that.
- **Not a hosted service.** The whole point is local jsonl files.
- **Not opinionated about your agent framework.** Pass `Recorder` around manually — there's nothing to integrate.

## License

MIT.
