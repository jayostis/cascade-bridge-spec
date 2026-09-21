# The adapter manifest

An adapter's manifest is an RO-Crate 1.2, `ro-crate-metadata.json` at the package
root. What the root entity carries is [`profile/must/adapter.ttl`](profile/must/adapter.ttl);
[`../fixtures/synthetic-adapter/ro-crate-metadata.json`](../fixtures/synthetic-adapter/ro-crate-metadata.json)
is a crate that passes.

Two things the shapes cannot make obvious:

- **`conformsTo` is `dcterms:conformsTo`**, not a schema.org term: a query using
  `schema:conformsTo` matches nothing.
- **Every `bridge:` key must also be in `@context`.** JSON-LD expands it from the
  prefix alone, so only RO-Crate 1.2's own check fails.
