# Building an engine

A Bridge runs adapters: it owns every stage, and an adapter contributes data to
them. Read:

1. [`stages.md`](stages.md): the stages around a mapping.
2. [`sparql.md`](sparql.md): the `sparql-1.1` profile. Normative.
3. [`executing.md`](executing.md): running an adapter's test manifest.
4. [`command.md`](command.md): the command you offer. Normative.

How each test type is judged is its `rdfs:comment` in
[`../vocab/bridge.ttl`](../vocab/bridge.ttl): implement that, not a paraphrase.
