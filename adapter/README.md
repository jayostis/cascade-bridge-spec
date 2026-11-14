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

## Naming a source's kinds of record

Some sources name a kind of record by an identifier, as a C-CDA names a template by its `templateId` root, and a tool
showing the adapter to a reader needs the name in words. Where the adapter's `bridge:inSourceRecordType` values are
identifiers, declare it with `bridge:sourceRecordTypesAreIdentifiers true` on the adapter in the crate (and the term in
the crate's `@context`). An adapter that declares nothing, or false, is not checked: a FHIR resource type is already a name.

When it is declared, each `bridge:inSourceRecordType` value of the accounting is the `skos:notation` of one `skos:Concept`
written in the same file `bridge:sourceAccounting` names, carrying one `skos:prefLabel`, a name in words that is not the
id itself, and a `dct:source` naming where the source publishes the name (the check does not read `dct:source`).
Checked by [`profile/must/record_type_names.py`](profile/must/record_type_names.py).

```turtle
<https://example.org/templates/2.16.840.1.113883.10.20.22.4.7> a skos:Concept ;
  skos:notation "2.16.840.1.113883.10.20.22.4.7" ;
  skos:prefLabel "Allergy - Intolerance Observation"@en ;
  dct:source <https://www.hl7.org/ccdasearch/templates/2.16.840.1.113883.10.20.22.4.7.html> .
```

## Saying which issue tracks a gap

Link the issue or pull request that tracks a gap from the gap with `rdfs:seeAlso`. It is optional, and a gap may carry
more than one. Each value is an IRI of the form `https://github.com/<owner>/<repo>/issues/<n>` or
`https://github.com/<owner>/<repo>/pull/<n>`, with nothing after the number, no trailing slash, query or fragment; the shape
in [`../shapes/gap-scheme.shapes.ttl`](../shapes/gap-scheme.shapes.ttl) refuses any other value. It is not
`bridge:closedBy`, which names the Cascade term that would let the adapter carry the gap.

## Saying where a place stands in each form of a path

Some formats write one place several ways: FHIR writes the same element at the top of a resource, in a Bundle's entry, in a
resource another contains and in one a Bundle's entry contains. A tool reading the adapter, and an explorer of it, must be
told these are one place. An envelope says it with optional properties, each a path of the source format
(for JSON, as in [`engine/sparql.md`](../engine/sparql.md)), defined in [`vocab/bridge.ttl`](../vocab/bridge.ttl) and checked by
[`profile/must/envelope.ttl`](profile/must/envelope.ttl):

| property | FHIR R4, Bundle envelope | FHIR R4, resource envelope |
|---|---|---|
| `bridge:pathOfContentInRecord` | `/resource` | empty |
| `bridge:pathOfContainedContentBelowContent` | `/contained` | `/contained` |
| `bridge:pathOfRecordKindBelowContent` | `/resourceType` | `/resourceType` |

A `bridge:sourcePath` that begins with a form's prefix and a `/` is that prefix, the form, and the place after it; the
longest prefix is the form. An envelope's content form has its `bridge:pathOfContentInRecord` as its prefix, and its contained
form that and its `bridge:pathOfContainedContentBelowContent`. An envelope that declares none of the three has no form, and an
adapter with no form reads each path as its own place. No two envelopes of an adapter declare the same prefix, and a prefix
must not equal a real member name of the source in another form: a `resource` member of a record read in the resource
envelope would make `/resource/code` read as the Bundle form.
