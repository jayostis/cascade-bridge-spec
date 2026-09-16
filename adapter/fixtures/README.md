# Fixtures and provenance

Every file an adapter ships and every dataset it references is an entity in the
crate, and what each must carry is checked by [`../profile/must/`](../profile/must/).

## Digests

`sha256` is the local claim: these bytes, here. A publisher's own digest, such as
the `.md5` published beside a release, is recorded too under its own term: it is
the publisher's claim about the file at its source, a different assertion, and
the two are not merged.

**A digested file is a byte-for-byte copy and is never edited.** Changing one
means replacing it from its source and restating its digest and size in the same
commit. Protect such files from line-ending normalisation and save-time trimming
in `.gitattributes` and `.editorconfig`, or the digests quietly stop being true.

**What is not known is recorded as not known.** A provenance record whose gaps
are invisible is worse than none: a reader cannot tell a fact from a silence.

## Large datasets are referenced, not committed

The line is not a byte count but whether the bytes can be held to a digest for
the life of the pin. A dated release file can be; a "latest" pointer cannot, and
is not something a Bridge can be asked to run.

## The triplet

```
fixtures/in/<name>.<ext>            the source document
fixtures/expected/<name>.ttl        the graph it must produce
fixtures/findings/<name>.gaps.json  the findings it must produce
```

`<name>` is the test's `mf:name`. Each expected graph names its input with
`isBasedOn`, so a query walks from result to input without matching file names.

## The findings model is not settled

Today a findings sidecar is a JSON array of `sourceField`, `reason`, `severity`,
`context` records ([`../../engine/sparql.md`](../../engine/sparql.md)). It is a
private shape, and it should not stay one.

One canonical findings model belongs inside the Bridge, and two published forms
fit, split by what a finding is about: SHACL validation results for a finding
about the produced graph, and the W3C Web Annotation Data Model for a finding
about the source document, where an `oa:XPathSelector` is what `sourceField`
already is. Existing oracles are asserted byte for byte against `gaps.json`, so
the choice is not made here. It has to be made **before a second adapter writes
findings**: two shapes in the wild is the decision taken by accident.
