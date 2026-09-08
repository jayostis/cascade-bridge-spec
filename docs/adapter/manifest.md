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
shapes in [`shapes/bridge.shapes.ttl`](../../shapes/bridge.shapes.ttl) are the
checks instead.

## The root entity is the adapter

The crate's root entity, `./`, is typed `["Dataset", "bridge:Adapter"]`.
Schema.org carries what it can, Dublin Core carries `conformsTo` (the RO-Crate
context expands that key to `dcterms:conformsTo`, not a schema.org term, so a
query written with `schema:conformsTo` matches nothing), and the `bridge:`
vocabulary carries what neither has.

Every cardinality below is enforced by `<#Adapter>` in the shapes; every term is
declared with an `rdfs:comment` in [`vocab/bridge.ttl`](../../vocab/bridge.ttl).

| property | cardinality | value | what it is |
|---|---|---|---|
| `identifier` | exactly 1 | string, `^[a-z][a-z0-9-]*$` | the format id a Bridge routes on. `clinvar` in the pilot, the same string `cascade-cli` accepts for `--from` |
| `name` | exactly 1 | string | the human name of the source format |
| `version` | exactly 1 | string, semver | the adapter package's own version, the one its `CHANGELOG.md` carries |
| `license` | exactly 1 | IRI | the SPDX licence entity for the package |
| `conformsTo` | 1 or more | IRI | what the adapter is written against. The profile IRI below is how conformance to this specification is declared |
| `bridge:profileRequired` | 0 or more | IRI, a `bridge:Profile` | a Bridge profile needed beyond Core. An adapter that needs Core only names none |
| `bridge:specPin` | exactly 1 | IRI | the commit of the Cascade Bridge Specification the adapter is written against |
| `bridge:vocabularyPin` | exactly 1 | IRI | the `spec` commit the adapter's Cascade vocabularies are pinned to |
| `bridge:vocabulary` | 1 or more | IRI | a Cascade vocabulary the adapter writes, by namespace |
| `bridge:sourceMediaType` | exactly 1 | string | IANA media type of the source documents |
| `bridge:sourceSchema` | exactly 1 | IRI, a crate `File` | the pinned source-side schema every unit is validated against |
| `bridge:envelope` | 1 or more | IRI, a `bridge:Envelope` | a document root the format arrives in |
| `bridge:unit` | exactly 1 | string | the element a Bridge splits a document on |
| `bridge:detectXPath` | exactly 1 | string | the content-based router's rule |
| `bridge:table` | 0 or more | IRI, a crate `File` | a lookup table the mapping reads. Phase 2 |
| `bridge:extensionVocabulary` | at most 1 | IRI | the adapter's own namespace for values with no Cascade term. Phase 2 |
| `bridge:testManifest` | exactly 1 | IRI, an `mf:Manifest` | the test manifest a Bridge's harness executes |

An adapter **does not declare a tier**. a tier is measured, by
running the adapter's fixtures on every published Bridge, and recorded in a
catalogue, which is a repository downstream of every adapter and every Bridge and
is no part of this one ([`alignment.md`](../pinning.md)).
`bridge:tier`, `bridge:Universal` and `bridge:Limited` existed in the
pilot's copy of the vocabulary and were removed in the move to this repository.
What a lint may compute from the package alone is a *candidate*, never a claim;
[`validation.md`](validation.md) says what it computes and in what words.

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
described by [`profile/ro-crate-metadata.json`](../../profile/ro-crate-metadata.json),
an RO-Crate Profile Crate whose constraints resource is the SHACL shapes. The
IRI does not dereference yet; until it does, the specification is read from this
repository, and the IRI is an identifier rather than a location.

The pin is an entity, not a string: a `SoftwareSourceCode` in the crate with
`codeRepository` and `version` (the full SHA), the same shape
`bridge:vocabularyPin` uses and the same shape
`conformance/scripts/SPEC_PIN` carries as `repo=` and `commit=`. Every commit an
adapter pins is tagged in the repository it pins, for the reason SPEC_PIN
records: a branch tip is not a guarantee, and a pin to an untagged commit dies
at `git checkout` the first time a branch is reset. [`alignment.md`](../pinning.md)
is the whole of that discipline.

## Envelope entities

An envelope is a document root the source format arrives in. A Bridge accepts
any of the adapter's envelopes and splits each on the unit.

| property | cardinality | value |
|---|---|---|
| `name` | exactly 1 | string, `^[a-z][a-z0-9-]*$`, the short id a test action's envelope reference is read as |
| `bridge:rootElement` | exactly 1 | local name of the document element |
| `bridge:documentSchema` | at most 1 | IRI, a crate `File`: a schema that validates a whole document in this envelope |

`bridge:documentSchema` is absent when the source schema declares the root
directly, and present when it does not. In the pilot, NCBI's XSD declares the
release root `ClinVarVariationRelease` but not the efetch root
`ClinVarResult-Set`, so the efetch envelope names a wrapper schema that includes
NCBI's unchanged and adds that one element, and the release envelope names none.

Envelopes are entities so that the test manifest can refer to one by IRI and the
shapes can check the reference resolves to a `bridge:Envelope` the adapter
lists. That check is the reason envelopes are not strings.

## The detect XPath

`bridge:detectXPath` is the rule a Bridge's content-based router applies to
decide that this adapter handles an input: **one XPath 3.1 expression**,
evaluated with the document node as the context item, whose effective boolean
value is true when the adapter handles the document. The pilot's is

```
exists(/(ClinVarResult-Set|ClinVarVariationRelease)/VariationArchive)
```

— the document element is one of the two envelope roots and it contains the
unit. One expression rather than a root-element field and a contains field,
because a format's detect rule is a predicate over a document and XPath is the
language for writing one; a two-field rule of the specification's own invention
would be a third thing to implement in every Bridge.

Not specified: what a router does when two adapters' detect rules are both true
for one document, and whether an adapter may declare a precedence. Nothing here
answers it, and no adapter should be written to depend on
an answer.

## What an adapter with a mapping adds

Three additions, none of which changes anything above. Import only; the export
direction is not specified.

- **The mapping, under Workflow RO-Crate.** When an adapter has a mapping, the
  crate takes the Workflow RO-Crate profile beside this one and names the entry
  transformation as its `mainEntity`, with `programmingLanguage` declared. That
  is a published profile for exactly this — a package whose point is a
  transformation — so no `bridge:` term is minted for it.
- **Tables.** `bridge:table` names each lookup table the mapping reads, as a
  crate `File` whose `schema:isBasedOn` says where its rows came from and whose
  `schema:license` is stated where it differs from the package's. A table is
  data a mapping reads, never a function it calls. Where a table
  is a mapping from source phrases to Cascade terms it is a concept map, and
  SKOS in Turtle is the form to write it in: it joins the same graph as the
  crate and the manifest, and no CSV convention has to be invented.
- **The extension vocabulary.** `bridge:extensionVocabulary` names the adapter's
  own namespace for values that have no Cascade term, at most one, its file a
  `File` in `hasPart`. Terms in it are the adapter's. No `cascade:` term is ever
  minted in an adapter; those go through spec's own process.
