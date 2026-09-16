# Fixtures and provenance

Every file an adapter ships and every dataset it references is described in the
adapter's crate. The crate is the manifest and the provenance record in one
graph ([`../ro-crate-metadata.md`](../ro-crate-metadata.md)); this document is the part
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

No shape enforces that list: only `encodingFormat` is checked
([`../profile/must/media_types.ttl`](../profile/must/media_types.ttl)), and the
rest is held up by `inventory.py` and `digests.py` in
[`../profile/must/`](../profile/must/).

`sha256` is the local claim: these bytes, here, now. Where the publisher also
publishes a digest — NCBI publishes an `.md5` beside every ClinVar release and
every XSD — that digest is recorded too, under its own term, as the *publisher's*
claim about the file at its source. The two are different assertions and are not
merged.

**What is not known is recorded as not known.** An input copied from somewhere
that did not record when or how it was fetched gets a crate entry saying exactly
that. A provenance record whose gaps are invisible is worse than one with none,
because a reader cannot tell a fact from a silence.

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
([`manifest.md`](manifest.md)).

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
so that a copy stays traceable to its origin. Where a name misdescribes the
record inside it, the crate entry and the test's `rdfs:comment` state the actual
record; renaming the file would break the trace and fix nothing.

Each expected graph is linked to its input in the crate with `isBasedOn`, so a
query can walk from a test through its result to the input the result was
derived from without matching on file names.

## The findings sidecar, and the question it leaves open

**As it stands today**, a findings sidecar is a four-field JSON
record — `sourceField`, `reason`, `severity`, `context` — one entry per thing the
mapping could not carry across. It is a private shape, and it is what the oracles
are asserted against, so it is what an adapter writes today.

The order the entries happen to be in is **not** part of the comparison, and the
sort order to write a new sidecar in is a recommendation and not a judgement:
both are `bridge:IsomorphicConversionTest`'s rule, and
[`manifest.md`](manifest.md) is why it is that. It is why the copied sidecars are
left in the ICU collation their authoring script produced.

**It should not stay private, and this specification does not settle it.** One
canonical findings model belongs inside the Bridge, and two published forms fit,
split by what a finding is about: SHACL validation results for a finding about
the produced graph, which the validate stage already emits, and the W3C Web
Annotation Data Model for a finding about the source document, where an
`oa:XPathSelector` is what `sourceField` already is in all but syntax.

The choice cannot be made here, because existing oracles are asserted byte for
byte and an adapter holding them must keep writing `gaps.json`. It has to be made
**before a second adapter writes findings**: two shapes in the wild is the
decision taken by accident.
