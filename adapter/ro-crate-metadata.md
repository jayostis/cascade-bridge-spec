# The adapter manifest

An adapter package's manifest is an **RO-Crate 1.2** at the package root,
`ro-crate-metadata.json`. There is no separate manifest file: the crate is both
what the adapter says about itself and the provenance record for every file and
remote dataset it names, in one JSON-LD graph.

There is no `adapter.yaml`. Everything an adapter says about itself belongs in
one graph, so that a reference is a link SHACL can check rather than a string
that could disagree with the thing it names.

The cost is stated rather than hidden: JSON-LD is less pleasant to hand-edit
than YAML and has no field completion. The RO-Crate validator and the SHACL
shapes in [`shapes/bridge.shapes.ttl`](../shapes/bridge.shapes.ttl) are the
checks instead.

## The root entity is the adapter

The crate's root entity, `./`, is typed `["Dataset", "bridge:Adapter"]`.
Schema.org carries what it can, Dublin Core carries `conformsTo` (the RO-Crate
context expands that key to `dcterms:conformsTo`, not a schema.org term, so a
query written with `schema:conformsTo` matches nothing), and the `bridge:`
vocabulary carries what neither has.

**What the root entity carries is `<#Adapter>` in
[`shapes/bridge.shapes.ttl`](../shapes/bridge.shapes.ttl).** Every property it
declares, with its cardinality, its value and the message a violation reports, is
there; what each term means is its `rdfs:comment` in
[`vocab/bridge.ttl`](../vocab/bridge.ttl). Read the properties from those two.
There is no list of them here, because a list here would be a second contract
with nothing keeping it honest.

The rest of this document is what neither file has room for: why the crate is
shaped this way, and the three parts of it — conformance, the detect query and
the mapping — a first adapter gets wrong.

### Declaring conformance

Two properties together:

```jsonc
"conformsTo": [
  { "@id": "https://ns.cascadeprotocol.org/bridge/v1-draft/adapter-profile/" }
],
"bridge:specPin": {
  "@id": "https://github.com/jayostis/cascade-bridge-spec/commit/<full SHA>"
}
```

`conformsTo` naming
`https://ns.cascadeprotocol.org/bridge/v1-draft/adapter-profile/` says *which
contract*; `bridge:specPin` says *which revision of it*. The profile IRI is
described by [`adapter/profile/ro-crate-metadata.json`](profile/ro-crate-metadata.json),
an RO-Crate Profile Crate whose constraints resource is the SHACL shapes. The
IRI does not dereference yet; until it does, the specification is read from this
repository, and the IRI is an identifier rather than a location.

The pin is an entity, not a string: a `SoftwareSourceCode` in the crate with
`codeRepository` and `version` (the full SHA), the same shape
`bridge:vocabularyPin` uses. By the time the adapter merges, the commit it names
is on this repository's default branch; [`pinning.md`](../pinning.md) says why.

### What RO-Crate 1.2 requires beyond the properties

Four things no property of the adapter states, each of which fails check 1 or
check 2 when missing. The lint's own test subject,
[`fixtures/synthetic-adapter`](../fixtures/synthetic-adapter/ro-crate-metadata.json),
is a crate that has them all.

- **Every `bridge:` key is declared in `@context`**, each as itself
  (`"bridge:specPin": "bridge:specPin"`), beside the `bridge` prefix. The prefix
  alone does not declare a key.
- **The profile IRI is an entity** typed `Profile`: RO-Crate requires what
  `conformsTo` names to be described in the crate.
- **Each pin is typed `["SoftwareSourceCode", "File"]` and listed in the root's
  `hasPart`.** RO-Crate reads a `SoftwareSourceCode` as a script, and a script
  must be a data entity.
- **Each profile in `bridge:profileRequired` is an entity typed
  `bridge:Profile`** in the crate: the shapes check the type in the crate's own
  graph, not in the vocabulary.

## Envelope entities

An envelope is a document root the source format arrives in. A Bridge accepts
any of the adapter's envelopes and splits each on the unit. What one carries is
`<#Envelope>` in the shapes.

`bridge:documentSchema` is absent when the source schema declares the root
directly, and present when it does not. In the pilot, NCBI's XSD declares the
release root `ClinVarVariationRelease` but not the efetch root
`ClinVarResult-Set`, so the efetch envelope names a wrapper schema that includes
NCBI's unchanged and adds that one element, and the release envelope names none.

Envelopes are entities so that the test manifest can refer to one by IRI and the
shapes can check the reference resolves to a `bridge:Envelope` the adapter
lists. That check is the reason envelopes are not strings.

## The detect query

`bridge:detectQuery` is the rule a Bridge's content-based router applies to
decide that this adapter handles an input: **one SPARQL 1.1 ASK**, evaluated
over the document's envelope skeleton
([`../engine/sparql.md`](../engine/sparql.md)), true when the adapter handles
the document. For the pilot, that the document element is one of its two
envelope roots and holds the unit:

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

One query rather than a root-element field and a contains field, because a
detect rule is a predicate over a document and SPARQL is the language the
profile already runs; a two-field rule of the specification's own invention
would be a second thing to implement in every Bridge.

Not specified: what a router does when two adapters' detect rules are both true
for one document, and whether an adapter may declare a precedence. Nothing here
answers it, and no adapter should be written to depend on
an answer.

## The mapping

The mapping is one or more SPARQL 1.1 CONSTRUCTs: the crate `File`s the root's
`bridge:mapping` names, each declared `application/sparql-query`, run under
`bridge:sparql-1.1`, which every adapter therefore requires. A Bridge runs every
one over each unit's lift, and the unit's graph is the union of their results;
the SELECTs `bridge:findingsQuery` names produce the unit's findings. The lift
and the invocation are [`../engine/sparql.md`](../engine/sparql.md). The term is
`bridge:mapping` rather than Workflow RO-Crate's `mainEntity`, which names one
entry point, because SPARQL has no module system: a mapping in several queries
is several files. The lint checks that the queries are declared and parse, and
never runs them. Import only; the export direction is not specified.

Two properties are optional:

- **Tables.** `bridge:table` names each lookup table the mapping reads, as a
  crate `File` whose `schema:isBasedOn` says where its rows came from and whose
  `schema:license` is stated where it differs from the package's. A table is
  data a mapping reads, never a function it calls: one declared `text/turtle`
  is loaded beside each unit's lift, and no other table format is specified.
  Where a table is a mapping from source phrases to Cascade terms it is a
  concept map, and SKOS in Turtle is the form to write it in: it joins the
  unit's graph, and no CSV convention has to be invented.
- **The extension vocabulary.** `bridge:extensionVocabulary` names the adapter's
  own namespace for values that have no Cascade term, at most one, its file a
  `File` in `hasPart`. Terms in it are the adapter's. No `cascade:` term is ever
  minted in an adapter; those go through spec's own process.
