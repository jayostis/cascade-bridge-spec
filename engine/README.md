# Building an engine

An engine (a Cascade Bridge) runs adapters.

| to find out | look at |
|---|---|
| the lift your output must reproduce, input by input | [`../fixtures/lift/`](../fixtures/lift/): each `.xml` and the `.nt` it must lift to, listed in `manifest.ttl` |
| the rules the lift follows | [`sparql.md`](sparql.md) |
| the names your mappings mint, inputs to name, and the SPARQL computing one | [`../fixtures/naming/`](../fixtures/naming/): `manifest.ttl` and `name.rq` |
| the versions you name, mapped graph to named graph through each version's canonical N-Quads | [`../fixtures/versioning/`](../fixtures/versioning/): each `.mapped.nt`, its `.nq` and its `.versioned.nt`, listed in `manifest.ttl` |
| how each test type is judged | the test types' `rdfs:comment` in [`../vocab/bridge.ttl`](../vocab/bridge.ttl) |
| an adapter to run | [`../fixtures/synthetic-adapter/`](../fixtures/synthetic-adapter/) |
| the facts a caller supplies with a document, and a file of them | [`../shapes/facts.shapes.ttl`](../shapes/facts.shapes.ttl) and [`../fixtures/synthetic-adapter/fixtures/facts/`](../fixtures/synthetic-adapter/fixtures/facts/) |
| a document's whole graph: records, versions, arrivals, the document and the import | [`../fixtures/synthetic-adapter/fixtures/expected/`](../fixtures/synthetic-adapter/fixtures/expected/) |
| the checkout its `bridge:cascadeVocabularyPin` names, to pass as `--vocabularies` | [`../fixtures/synthetic-vocabularies/`](../fixtures/synthetic-vocabularies/) |
| the commands you must offer | [`command.md`](command.md) |
| the smallest thing that meets them | [`../fixtures/fake-engine/engine.py`](../fixtures/fake-engine/engine.py) |
| loading and reporting a test manifest | [`executing.md`](executing.md) |
| each fault of a report, over it and the adapter's test manifest; none means it holds | [`faults-of-a-report.rq`](faults-of-a-report.rq) |
| the stages around a mapping | [`stages.md`](stages.md) |
| which adapters you must pass with, and the workflow your CI runs | [`../compatibility.md`](../compatibility.md) |
