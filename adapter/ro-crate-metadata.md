# The adapter manifest

An adapter's manifest is an **RO-Crate 1.2**, `ro-crate-metadata.json` at the
package root. There is no `adapter.yaml`: in one JSON-LD graph a reference is a
link SHACL can check, not a string that can disagree with what it names. The
cost is hand-editing JSON-LD; [`profile/`](profile/) is the check instead.

What the root entity carries is [`profile/must/adapter.ttl`](profile/must/adapter.ttl);
what each term means is its `rdfs:comment` in
[`../vocab/bridge.ttl`](../vocab/bridge.ttl).
[`../fixtures/synthetic-adapter/ro-crate-metadata.json`](../fixtures/synthetic-adapter/ro-crate-metadata.json)
is a crate that passes.

## What trips a first adapter

- **`conformsTo` is Dublin Core, not schema.org.** The RO-Crate context expands it
  to `dcterms:conformsTo`, so a query using `schema:conformsTo` matches nothing.
- **Every `bridge:` key must also be in `@context`.** JSON-LD expands it from the
  prefix alone, so the graph and the shapes are fine; RO-Crate 1.2's own
  requirements are what fail.
- **Envelopes and pins are entities, not strings**, so the shapes can check that
  a reference resolves to the thing it names.

## Why the queries look like this

**One ASK for detection**, rather than a root-element field and a contains field:
a detect rule is a predicate over a document, and SPARQL is the language the
profile already runs. A two-field rule of this specification's own would be a
second thing every Bridge implements. For example, a document element that is one
of two envelope roots and holds the unit:

```sparql
PREFIX fx:  <http://sparql.xyz/facade-x/ns/>
PREFIX xyz: <http://sparql.xyz/facade-x/data/>
ASK {
  ?root a fx:root ; ?slot ?unit .
  ?unit a xyz:VariationArchive .
  { ?root a xyz:ClinVarResult-Set }
  UNION { ?root a xyz:ClinVarVariationRelease }
}
```

**`bridge:mapping`, not Workflow RO-Crate's `mainEntity`**, because `mainEntity`
names one entry point and SPARQL has no module system: a mapping in several
queries is several files.

**A table is data a mapping reads, never a function it calls.** A table mapping
source phrases to Cascade terms is a concept map; write it as SKOS in Turtle.
