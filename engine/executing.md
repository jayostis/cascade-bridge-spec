# Executing a test manifest

**Load the crate and the manifest as one graph**: `ro-crate-metadata.json` as
JSON-LD and the manifest as Turtle, each with its own file location as base. Only
then does the manifest's `<../>` resolve to the crate's root entity, and an entry
lead to its input's digest or its envelope's schema by link rather than by file
name. With the wrong base every link becomes two unrelated nodes, and the shapes
report nothing rather than a mistake.

**Execute the entry's type, not its file name.** Each type's rule is its
`rdfs:comment` in [`../vocab/bridge.ttl`](../vocab/bridge.ttl). A Bridge offering
`bridge:sparql-1.1` also executes
[`../fixtures/lift/manifest.ttl`](../fixtures/lift/manifest.ttl), loaded on its
own.

**Report in EARL**: one `earl:Assertion` per entry, `earl:test` the entry's IRI,
`earl:subject` the Bridge, `earl:mode earl:automatic`, and an `earl:TestResult`
carrying the `earl:outcome`, the form every W3C test suite's reports take. A
report is never written back to the adapter: it measures one pairing at one pair
of commits, and stored anywhere it goes stale.
