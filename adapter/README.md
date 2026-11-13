# Building an adapter

An adapter is a package of data for one XML or JSON source format, with no code in it.

| to find out | look at |
|---|---|
| what a working package looks like, to copy | [`../fixtures/synthetic-adapter/`](../fixtures/synthetic-adapter/) for XML, [`../fixtures/synthetic-json-adapter/`](../fixtures/synthetic-json-adapter/) for JSON |
| what is checked, one requirement per file | [`profile/must/`](profile/must/) |
| how each requirement behaves, one test per rule | [`../tests/adapter_profile/`](../tests/adapter_profile/), `test_<requirement>.py` |
| whether your package passes | [`validation.md`](validation.md) |
| what a term means | [`../vocab/bridge.ttl`](../vocab/bridge.ttl) |
| what your queries run over | [`../engine/sparql.md`](../engine/sparql.md) |

A failing run prints what was wanted. The rest of this directory is what none of
the above can show: [`ro-crate-metadata.md`](ro-crate-metadata.md),
[`fixtures/README.md`](fixtures/README.md), [`fixtures/manifest.md`](fixtures/manifest.md).

## Saying what a mapping is about

A reader asks how an adapter handles codes, dates, references, who the patient is or free text. Tag what answers
with `bridge:concern`, one concept of the scheme `bridge:concerns`
(`https://ns.cascadeprotocol.org/bridge/v1-draft#concerns`): `bridge:concernCodes`, `bridge:concernDates`,
`bridge:concernReferences`, `bridge:concernIdentity` or `bridge:concernText`. The tag is optional and at most one, on

| what is tagged | where it is written | what checks it |
|---|---|---|
| an accounting entry | the `bridge:PathEntry` in the file `bridge:sourceAccounting` names | [`profile/must/source_accounting.py`](profile/must/source_accounting.py) |
| a gap | the `skos:Concept` in the file `bridge:gapScheme` names | [`profile/must/gap_scheme.py`](profile/must/gap_scheme.py) |
| a test case | the test in the manifest `bridge:testManifest` names | [`profile/must/shapes.py`](profile/must/shapes.py) |

## Saying where a place stands in each form of a path

Some formats write one place several ways: FHIR writes the same element at the top of a resource, in a Bundle's entry, in a
resource another contains and in one a Bundle's entry contains. A tool reading the adapter, and an explorer of it, must be
told these are one place. An envelope says it with up to three optional properties, each a path of the source format
(for JSON, as in [`engine/sparql.md`](../engine/sparql.md)), checked by [`profile/must/envelope.ttl`](profile/must/envelope.ttl):

| property | the path it gives | FHIR R4, Bundle envelope | FHIR R4, resource envelope |
|---|---|---|---|
| `bridge:pathOfContentInRecord` | where the format's own content begins in a record read in the envelope; empty where the record is the content | `/resource` | empty |
| `bridge:pathOfContainedContent` | where, below that content, the content of a nested record begins | `/contained` | `/contained` |
| `bridge:pathOfRecordKind` | where, below the content, the record names its kind; the same below contained content | `/resourceType` | `/resourceType` |

A `bridge:sourcePath` that begins with a form's prefix and a `/` is that prefix, the form, and the place after it; the
longest prefix is the form. The forms an adapter has are the content form of each of its envelopes, and the contained
form of each that gives a contained path. An adapter that declares nothing has one form, the path itself. Each term is
named in the crate's `@context`. [`scripts/path_forms.py`](../scripts/path_forms.py) reads the forms and the place of a path
from a crate's graph.
