# Building an adapter

An adapter is a package of **data** for one source format. It contains no code:
the thing that runs it is a Bridge. If you are writing one, everything you need
is in this directory, in this order.

1. [`manifest.md`](manifest.md) — `ro-crate-metadata.json`, the one file that is
   both what your adapter says about itself and the provenance of everything it
   ships. Start here; the rest hangs off it.
2. [`fixtures.md`](fixtures.md) — what to commit and what to reference, the
   digests each carries, and the input / expected / findings triplet.
3. [`test-manifest.md`](test-manifest.md) — declaring your cases, and how each
   one is judged.
4. [`validation.md`](validation.md) — the six checks your package must pass, and
   how to run them locally and in your CI.

Also relevant, and short: [`../pinning.md`](../pinning.md), for how your adapter
names the revision of this specification it is written against, and why that
revision must be a tag.

You do not need [`../engine/`](../engine/). That is how a Bridge executes what
you declare; nothing there changes what you write.

The normative term definitions are [`../../vocab/bridge.ttl`](../../vocab/bridge.ttl)
and the constraints your package is checked against are
[`../../shapes/bridge.shapes.ttl`](../../shapes/bridge.shapes.ttl). Where a
document here and those files disagree, the Turtle is right.
