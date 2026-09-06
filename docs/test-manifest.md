# The test manifest

An adapter declares its fixtures, and how each is judged, as **a W3C-style test
manifest in Turtle**. The adapter's crate names it with `bridge:testManifest`;
the pilot's is at `fixtures/manifest.ttl`. A Bridge's harness executes it.
Nothing in an adapter package runs it, and nothing in an adapter package is a
test runner.

## Why this shape

A test manifest for RDF conversion is a solved problem. Every W3C RDF-family
test suite — Turtle, SPARQL, JSON-LD, SHACL, RDF Dataset Canonicalization — is a
manifest written in RDF with W3C's `mf:` test-manifest vocabulary
(`http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#`), where each entry
has a type, an `mf:action` (the input) and an `mf:result` (the expected output),
and **the comparison rule is carried by the entry's type**. The RML test cases
follow the same pattern. Against that, a YAML dialect would be the invented
thing.

Three consequences that matter more than the convention:

1. **The cases and the provenance are one graph.** The crate is JSON-LD, the
   manifest is Turtle, and each is loaded with its own file location as base, so
   a dataset test names a release by the same IRI the crate describes it under,
   an action names its envelope by the crate's entity, and walking from a test
   to its input's digest and licence is a graph traversal rather than a string
   match.
2. **Validation is SHACL**, the project's own validation language and what the
   conformance suite already runs.
3. **Every RDF engine reads it identically.** Two Bridges parsing a YAML dialect
   the same way is a hope; parsing Turtle the same way is a W3C guarantee, and
   that guarantee is what the claim "one adapter, same graph, every runtime"
   (RFC section 11) rests on.

The cost is stated: Turtle gets syntax support and a SHACL check from ordinary
editor tooling, not the per-field completion a JSON Schema would give a YAML
file. Small, for a file that changes a few times a year.

**One contract, not a menu.** An adapter does not choose among test conventions
for the conformance claim, because every convention an adapter may choose is a
harness every Bridge must implement, and two adapters proving "universal" by
different rules prove different things. Profile-specific unit suites — XSpec
over an `xslt-3` mapping's modules, say — are a separate, optional, declared
matter, and are not part of the conformance claim.

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
expected sidecar entry for entry, in the conformance repository's sort order
(`sourceField`, `severity`, `reason`).

Isomorphism, not byte equality, because the Bridge's records are blank nodes and
blank node labels are not stable. RFC section 11 names RDF Dataset
Canonicalization (RDFC-1.0, W3C Recommendation 2024) as how to decide it
properly, and says so against the comparison the pilot's oracle uses today:
`cascade-cli`'s `tests/clinvar-conformance.test.ts` compares
`riot --output=nq | sort` byte for byte, which assumes the same thing without
deciding it.

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

A stamp is a triple a Bridge adds *after* the mapping (RFC section 5, "stamp";
the Enterprise Integration Patterns Message History): `cascade:dataProvenance`,
`cascade:schemaVersion`, source identity, import time. The stamp set is a
property of the Bridge's stamp stage, not of any one fixture.

So `bridge:ignorePredicate` is stated **once, on the `mf:Manifest`**, and every
entry inherits it. An entry that carries its own `bridge:ignorePredicate`
**replaces** the manifest's set for that entry alone — an override, not an
addition.

Stating it per entry was the earlier shape and was wrong in a way worth
recording: three identical triples repeated on every conversion test is three
places for the set to drift, and an adapter with twenty fixtures would have
sixty. A fact about the Bridge belongs where it is true once.

## What a harness owes

A harness executes the manifest; it does not interpret it. Concretely: it reads
the entry types rather than the file names, applies the rule the type carries,
removes the inherited or overridden stamp set from both sides before comparing,
and reports one result per entry. RFC section 11 and the phase 2 notes on the
pilot's issue put that report in **EARL** (W3C Evaluation and Report Language),
the form every W3C test suite's implementation reports take: one
`earl:Assertion` per manifest entry, with `earl:test` the entry's IRI,
`earl:subject` the Bridge, `earl:outcome` and `earl:mode automatic`. An
adapter's tier is then a query over those reports rather than a claim in the
adapter, and the catalogue is where the query's answer is recorded
([`alignment.md`](alignment.md)).

No Bridge exists, so no EARL report exists, and nothing in this repository has
yet executed a manifest. That is the honest state of the contract: written from
one adapter, checked by SHACL, and unproven until `cascade-bridge-java` runs it.
