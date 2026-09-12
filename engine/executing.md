# Executing a test manifest

What a Bridge's harness must do with an adapter's `fixtures/manifest.ttl`. The
manifest's shape is [`../adapter/fixtures/manifest.md`](../adapter/fixtures/manifest.md);
this is the other side of it.

## Load the crate and the manifest as one graph

Parse the adapter's `ro-crate-metadata.json` as JSON-LD and its test manifest as
Turtle, **each with its own file location as base**. Only then does the
manifest's `<../>` resolve to the crate's root entity and its `<in/x.xml>` to the
crate's `fixtures/in/x.xml` entity, and only then can a harness walk from an
entry to its input's digest, or from an action's envelope to the schema that
validates it, instead of matching on file names.

## Execute the entry, not the file name

A harness reads the entry's **type** and applies the rule that type carries. The
rules are normative in [`../vocab/bridge.ttl`](../vocab/bridge.ttl), as the
`rdfs:comment` on each of `bridge:IsomorphicConversionTest`,
`bridge:InputOnlyTest` and `bridge:DatasetCompletionTest`. They are not restated
here, and a harness that implements this document rather than those comments is
implementing the wrong thing.

Two obligations sit outside the individual rules:

- **Stamp predicates come off both sides first.** The set is the entry's
  `bridge:ignorePredicate` if it carries one, otherwise the manifest's. A Bridge
  writes its own stamps and an oracle carries whatever produced it, so a
  comparison that kept them would fail every correct implementation.
- **A comparison is insensitive to everything the format does not mean.** Blank
  node labels in a graph, element order in a findings array. A stricter rule than
  the format's meaning catches no mapping errors; it only fails harnesses that
  are right.

## Report in EARL

One `earl:Assertion` per manifest entry: `earl:test` the entry's IRI,
`earl:subject` the Bridge, `earl:mode earl:automatic`, and `earl:result` an
`earl:TestResult` whose `earl:outcome` is the result. That is the form every W3C
test suite's implementation reports take.

A report is never written back to the adapter it is about: a Bridge that pinned
an adapter would be claiming ownership of it, and an adapter that pinned a Bridge
would stop being portable ([`../pinning.md`](../pinning.md)).

No Bridge exists, so no EARL report exists and nothing here has executed a
manifest. The contract is written from one adapter and checked by SHACL; it is
unproven until an engine runs it.
