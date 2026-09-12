# Building an engine

A Bridge is the thing that runs adapters. It owns every stage around the
mapping; an adapter only contributes data to those stages. If you are writing
one, this directory is what you need.

1. [`stages.md`](stages.md) — the stages you run around an adapter's mapping,
   each named with the Enterprise Integration Pattern it already is, and what an
   adapter contributes to each.
2. [`executing.md`](executing.md) — running an adapter's test manifest: loading
   the crate and the manifest as one graph, applying each entry type's rule, and
   reporting in EARL.

Also relevant, and short: [`../pinning.md`](../pinning.md), for how you name the
revision of this specification you implement.

You do not need most of [`../adapter/`](../adapter/) — that is how a package is
authored. The exception is [`../adapter/test-manifest.md`](../adapter/test-manifest.md),
which is the shape of the file you will be executing, and
[`../adapter/manifest.md`](../adapter/manifest.md), which is the shape of the
crate you will be reading.

The normative term definitions are [`../../vocab/bridge.ttl`](../../vocab/bridge.ttl).
Each test type's `rdfs:comment` there carries the comparison rule you must
implement — implement those, not a prose paraphrase of them.
