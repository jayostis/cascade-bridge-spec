# The test manifest

An adapter declares its cases as **a W3C test manifest (`mf:`) in Turtle**, named
by the crate's `bridge:testManifest`. A Bridge's harness executes it
([`../../engine/executing.md`](../../engine/executing.md)); nothing in an adapter
package runs it.

What a manifest and its entries carry is `<#Manifest>` and the shapes below it in
[`../../shapes/bridge.shapes.ttl`](../../shapes/bridge.shapes.ttl). How each entry
type is judged is that type's `rdfs:comment` in
[`../../vocab/bridge.ttl`](../../vocab/bridge.ttl).

```turtle
<> a mf:Manifest ;
  rdfs:label "..." ;
  bridge:adapter <../> ;
  bridge:ignorePredicate cascade:dataProvenance, cascade:schemaVersion, prov:generatedAtTime ;
  mf:entries ( <#first> <#second> ) .
```

Relative IRIs resolve against the manifest's own location, so `<../>` is the
crate's root entity.

## Why

**One contract, not a menu.** Every test convention an adapter may choose is a
harness every Bridge must implement, and two adapters proving conformance by
different rules prove different things.

**A comparison is insensitive to everything the format does not mean.** A rule
stricter than the format's meaning catches no mapping errors; it only fails
harnesses that are right. That is why graphs compare up to blank node labels,
findings compare as a multiset, and stamps come off both sides.

**Isomorphism is decided properly by RDF Dataset Canonicalization** (RDFC-1.0).
Sorting N-Quads and comparing bytes assumes the answer rather than deciding it.

**A dataset completion test's result starts absent, not empty.** RDF has no null,
so the first run records the values rather than the author carrying placeholders.
