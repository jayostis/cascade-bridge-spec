# Building an engine

An engine (a Cascade Bridge) runs adapters.

| to find out | look at |
|---|---|
| the lift your output must reproduce, input by input | [`../fixtures/lift/`](../fixtures/lift/): each `.xml` and the `.nt` it must lift to, listed in `manifest.ttl` |
| the rules the lift follows | [`sparql.md`](sparql.md) |
| how each test type is judged | the test types' `rdfs:comment` in [`../vocab/bridge.ttl`](../vocab/bridge.ttl) |
| an adapter to run | [`../fixtures/synthetic-adapter/`](../fixtures/synthetic-adapter/) |
| the commands you must offer | [`command.md`](command.md) |
| the smallest thing that meets them | [`../fixtures/fake-engine/engine.py`](../fixtures/fake-engine/engine.py) |
| loading and reporting a test manifest | [`executing.md`](executing.md) |
| the stages around a mapping | [`stages.md`](stages.md) |
| which adapters you must pass with, and the workflow your CI runs | [`../compatibility.md`](../compatibility.md) |
