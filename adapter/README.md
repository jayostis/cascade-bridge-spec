# Building an adapter

An adapter is a package of data for one XML source format, with no code in it.

| to find out | look at |
|---|---|
| what a working package looks like, to copy | [`../fixtures/synthetic-adapter/`](../fixtures/synthetic-adapter/) |
| what is checked, one requirement per file | [`profile/must/`](profile/must/) |
| how each requirement behaves, one test per rule | [`../tests/adapter_profile/`](../tests/adapter_profile/), `test_<requirement>.py` |
| whether your package passes | [`validation.md`](validation.md) |
| what a term means | [`../vocab/bridge.ttl`](../vocab/bridge.ttl) |
| what your queries run over | [`../engine/sparql.md`](../engine/sparql.md) |

A failing run prints what was wanted. The rest of this directory is what none of
the above can show: [`ro-crate-metadata.md`](ro-crate-metadata.md),
[`fixtures/README.md`](fixtures/README.md), [`fixtures/manifest.md`](fixtures/manifest.md).
