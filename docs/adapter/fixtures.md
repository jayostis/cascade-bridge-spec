# Fixtures and provenance

Every file an adapter ships and every dataset it references is described in the
adapter's crate. The crate is the manifest and the provenance record in one
graph ([`manifest.md`](manifest.md)); this document is the part
of it that is about fixtures.

## Committed inputs are small, and carry a digest

An input small enough to commit is committed, as a crate `File` in the root
entity's `hasPart`, carrying at least:

| property | what it records |
|---|---|
| `encodingFormat` | the media type, so a lint can tell a fixture from a document |
| `contentSize` | the size in bytes |
| `sha256` | computed locally over the committed bytes |
| `license` | the source's terms, which are usually not the package's |
| `isBasedOn` | where the bytes came from: a URL, or a commit in another repository |
| `description` | what the record is, and what is not known about it |

`sha256` is the local claim: these bytes, here, now. Where the publisher also
publishes a digest — NCBI publishes an `.md5` beside every ClinVar release and
every XSD — that digest is recorded too, under its own term, as the *publisher's*
claim about the file at its source. The two are different assertions and are not
merged.

**What is not known is recorded as not known.** The pilot's four oracle inputs
were copied from another repository, and the date and method by which
they were originally fetched from NCBI were never recorded; each of their crate
entries says exactly that. A provenance record whose gaps are invisible is worse
than one with none, because a reader cannot tell a fact from a silence.

**Verbatim copies are never edited.** A file whose digest the crate records is a
byte-for-byte copy. Changing one means replacing it from its source and updating
the digest, size and description in the same commit. An adapter's
`.gitattributes` and `.editorconfig` should protect such files from line-ending
normalisation and from an editor's save-time trimming, or the digests quietly
stop being true — and comparing them against a sibling checkout's working tree
rather than against its git blobs will report every file as differing at the
first line ending, which is the failure that teaches someone to "fix" the copies
and break the digests.

## Large datasets are referenced, not committed

A multi-gigabyte release is a crate `Dataset` entity: a URL, a version or
release date, the publisher's digest, a size and a licence. A
`bridge:DatasetCompletionTest` in the test manifest names that entity by its
`@id`, and the shapes require the entity to carry a `schema:contentUrl`, because
a Bridge has to be able to fetch what it is asked to stream
([`test-manifest.md`](test-manifest.md)).

The dividing line is not a byte count but whether the bytes can be held to a
digest for the life of the pin. A published, dated release file can be. A
"latest" pointer cannot: it resolves to different bytes over time, and an entity
standing for one is a reference, not something to run.

## The triplet: input, expected, findings

A conversion fixture is three files with one stem:

```
fixtures/in/<name>.<ext>            the source document
fixtures/expected/<name>.ttl        the graph it must produce
fixtures/findings/<name>.gaps.json  the findings it must produce
```

The stem is the test's `mf:name` and its fragment IRI in the test manifest.

Names are kept from the source they were copied from even when they are wrong,
so that a copy stays traceable to its origin. Two of the pilot's four oracle
file names do not describe the record inside — a BRCA1 variant named BRCA2, a
VMA21 variant named MLH1. Renaming them would break the trace to their origin;
the crate entry and the test's `rdfs:comment` state the actual record instead.

Each expected graph is linked to its input in the crate with `isBasedOn`, so a
query can walk from a test through its result to the input the result was
derived from without matching on file names.

## The findings sidecar, and the question it leaves open

**As it stands today**, a findings sidecar is a four-field JSON
record — `sourceField`, `reason`, `severity`, `context` — one entry per thing the
mapping could not carry across. It is a private shape, and it is what the oracles
are asserted against, so it is what an adapter writes today.

The order the entries happen to be in is **not** part of the comparison:
`bridge:IsomorphicConversionTest` compares the array as a multiset
([`test-manifest.md`](test-manifest.md)). A sidecar written from scratch SHOULD
be sorted by Unicode code point on (`sourceField`, `severity`, `reason`), which
keeps regeneration diffs readable, but that is file hygiene and never a
judgement: the copied sidecars are in the ICU collation their
authoring script left them in and are not re-sorted.

**It should not stay private.** One canonical findings model belongs inside the
Bridge, into which source-side validation, the
mapping, the undeclared-predicate check, SHACL and the honesty differential all
land. Two published forms fit, split by what a finding is *about*:

- A finding **about the produced graph** is a SHACL validation result:
  `sh:focusNode`, `sh:resultPath`, `sh:resultMessage`, `sh:resultSeverity`. SHACL
  already provides the model, and the validate stage already produces it.
- A finding **about the source document** — which is what every one of the 1,306
  entries across the pilot's four oracles is — fits the W3C **Web Annotation Data
  Model**: an `oa:Annotation` whose target is the input file with an
  `oa:XPathSelector` naming the field, whose body is the reason, and whose
  motivation or a severity term carries `info` or `warning`. Today's
  `sourceField` is already an XPath in all but syntax, so the selector is a
  change of spelling rather than of content.

**The constraint that keeps the question open.** The sidecars are asserted byte
for byte against the existing converter's output, so an adapter whose oracles
are those files must keep writing `gaps.json` and let the Bridge map it. The
standard form is therefore a question to settle **before any second adapter
writes findings** — because the moment two adapters have
written findings in two shapes, the choice has been made by accident.

Until it is settled, this specification says only what is true: the sidecar is
the mapping's contribution to the Bridge's findings channel (the Enterprise
Integration Patterns Invalid Message Channel, [`stages.md`](../engine/stages.md)), it is
compared exactly, and its shape is not yet standard.
