# Executing a test manifest

**Load the crate and the manifest as one graph**: `ro-crate-metadata.json` as
JSON-LD and the manifest as Turtle, each with its own file location as base, so
the manifest's `<../>` is the crate's root entity.

**Apply each entry's type's rule**: its `rdfs:comment` in
[`../vocab/bridge.ttl`](../vocab/bridge.ttl). A Bridge offering
`bridge:sparql-1.1` also executes
[`../fixtures/lift/manifest.ttl`](../fixtures/lift/manifest.ttl), loaded on its own.

**Report in EARL**: one `earl:Assertion` per entry, `earl:test` the entry's IRI,
`earl:subject` the Bridge, `earl:mode earl:automatic`, and an `earl:TestResult`
carrying the `earl:outcome`. A report is never written back to the adapter.

Every entry is `earl:inapplicable` when the adapter requires a profile the
Bridge does not offer, and `earl:failed` when the adapter cannot be prepared.
Otherwise an entry of a type the Bridge does not know is `earl:inapplicable`,
and one that cannot be run is `earl:failed`.
