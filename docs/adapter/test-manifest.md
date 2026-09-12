# The test manifest

An adapter declares its fixtures, and how each is judged, as **a W3C-style test
manifest in Turtle**. The adapter's crate names it with `bridge:testManifest`;
the pilot's is at `fixtures/manifest.ttl`. A Bridge's harness executes it.
Nothing in an adapter package runs it, and nothing in an adapter package is a
test runner.

## One contract, not a menu

An adapter does not choose among test conventions. Every convention an adapter
may choose is a harness every Bridge must implement, and two adapters proving
"universal" by different rules prove different things. Profile-specific unit
suites — XSpec over an `xslt-3` mapping's modules, say — are optional, declared,
and no part of the conformance claim.

## The manifest

```turtle
<> a mf:Manifest ;
  rdfs:label "..." ;
  bridge:adapter <../> ;
  bridge:ignorePredicate cascade:dataProvenance, cascade:schemaVersion, prov:generatedAtTime ;
  mf:entries ( <#first> <#second> ) .
```

| property | cardinality | what it is |
|---|---|---|
| `bridge:adapter` | exactly 1 | the adapter's crate root entity, whose `bridge:testManifest` is this file. The shapes check both directions |
| `bridge:ignorePredicate` | 0 or more | the stamp set, below |
| `mf:entries` | exactly 1 | an RDF list, at least one member, every member typed with exactly one of the three test types |

Relative IRIs resolve against the manifest's own location. In the pilot, from
`fixtures/manifest.ttl`, `<>` is the crate's `fixtures/manifest.ttl` entity,
`<../>` is the crate's root entity, `<in/X.xml>` is the crate's
`fixtures/in/X.xml`, and `<../ro-crate-metadata.json#envelope-efetch>` is the
envelope the crate declares. Load either file with the wrong base and every one
of those links becomes two unrelated nodes, and the shapes then report nothing
rather than reporting a mistake.

## The three test types

The type is the comparison rule. Each is an `mf:ManifestEntry` with exactly one
`mf:name` (which is also its fragment IRI) and exactly one `mf:action`.

### `bridge:IsomorphicConversionTest`

A committed input with a committed expected graph and a committed expected
findings sidecar.

- `mf:action`: `bridge:input` (the committed source document, exactly one) and
  `bridge:envelope` (exactly one, an envelope the adapter lists). Closed: a
  property the shape does not declare is a mistake, not an extension.
- `mf:result`: `bridge:graph` (the expected Turtle) and `bridge:findings` (the
  expected sidecar), exactly one each. Also closed.

**The comparison rule.** Run the mapping on `bridge:input`. The produced graph
must be **isomorphic** to `bridge:graph` — blank nodes relabelled, IRIs and
literals exact — after every triple whose predicate is a `bridge:ignorePredicate`
has been removed from **both sides**. The produced findings must **equal** the
expected sidecar as a **multiset**: the same entries with the same multiplicity,
in any order, two entries being equal when they have the same member names and
equal values (JSON object equality, not byte equality).

Both halves of that are the same principle: **a comparison is insensitive to
everything the format does not mean.** A stricter rule than the format's meaning
does not catch more mapping errors; it only fails harnesses that are right.

Isomorphism, not byte equality, because the Bridge's records are blank nodes and
blank node labels are not stable. RDF Dataset Canonicalization (RDFC-1.0, W3C
Recommendation 2024) is how to decide it properly. The pilot's oracle compares
`riot --output=nq | sort` byte for byte, which assumes the same thing without
deciding it.

A multiset, not an ordered array, because no entry in a findings sidecar refers
to a position, so the order carries no meaning. The pilot's oracles were sorted
with `localeCompare`, which is ICU collation, in which `/` sorts before `@`
although U+002F is above U+0040; across its four committed sidecars, 78, 56, 6
and 1 adjacent pairs are out of code-point order.
A harness comparing with Java's `String.compareTo`, or with JavaScript's `<`,
puts the same correctly mapped entries in a different order and reports a false
failure. Requiring the committed order would make every Bridge carry ICU, and
pin a CLDR version nothing states, to compare a bookkeeping array.

Multiplicity **is** compared: entries do repeat, the repeats are identical whole
objects, and a set comparison would silently lose them.

Separately, and as file hygiene rather than judgement: a sidecar written from
scratch SHOULD be sorted by Unicode code point on (`sourceField`, `severity`,
`reason`), because every language reproduces code-point order identically and it
keeps regeneration diffs readable. That is a property of the file and never of
the comparison, so a sidecar copied verbatim from elsewhere is not re-sorted to
satisfy it.

### `bridge:InputOnlyTest`

A committed input with no expected output. Parse and validate `bridge:input`;
record the graph and findings a Bridge produces; judge nothing.

- `mf:action`: as above.
- `mf:result`: **none**. The shape sets `sh:maxCount 0`, because a result that is
  not judged is not a result.
- `bridge:ignorePredicate`: **none**, for the same reason. Nothing is compared,
  so there is nothing to exclude from a comparison.

This type exists so that an input whose provenance is worth having can be
committed and exercised before anyone has produced an expected graph for it. The
pilot uses it for NCBI's own published sample, the one input whose provenance is
unimpeachable.

### `bridge:DatasetCompletionTest`

A dataset too large to commit, streamed from where it is published.

- `mf:action`: `bridge:dataset` (exactly one, the `@id` of a crate `Dataset`
  entity) and `bridge:envelope` (exactly one). Closed.
- `mf:result`: at most one, holding `bridge:records` (a non-negative
  `xsd:integer`, the number of units processed) and `bridge:outputDigest` (the
  string `sha256:<64 lowercase hex>`, over the canonical N-Quads output with the
  stamp triples removed). Closed.

**The rule.** Stream the dataset in its envelope. The run must complete without
rejection. Where `bridge:records` and `bridge:outputDigest` are present they must
match; where absent, the harness records them.

Absent, not empty: RDF has no null, so the two unknown-until-run values are
written by the first run rather than carried as placeholders. A multi-gigabyte
expected output that fits in one line is the whole point of the type.

**The dataset must be fetchable.** `<#RunnableDataset>` in the shapes requires
the named crate `Dataset` to carry exactly one `schema:contentUrl`. An entity
that stands for a release but currently resolves to another file — a "latest"
symlink, say — has no content of its own, and is not something a Bridge can be
asked to run. Such a release joins the manifest when a dated file with its own
crate entity exists.

## Ignore predicates: stated once, inherited by every entry

A stamp is a triple a Bridge adds *after* the mapping (the Enterprise
Integration Patterns Message History): `cascade:dataProvenance`,
`cascade:schemaVersion`, source identity, import time. The stamp set is a
property of the Bridge's stamp stage, not of any one fixture.

So `bridge:ignorePredicate` is stated **once, on the `mf:Manifest`**, and every
entry inherits it. An entry that carries its own `bridge:ignorePredicate`
**replaces** the manifest's set for that entry alone — an override, not an
addition. Stated per entry, the set would repeat on every test and drift; a
fact about the Bridge belongs where it is true once.

## What a harness owes

The other side of this document is [`../engine/executing.md`](../engine/executing.md):
how a harness loads the two files as one graph, which rule it applies to each
entry type, and the EARL report it produces.
