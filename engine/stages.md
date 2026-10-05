# Engine stages

The stages a Bridge runs around an adapter's mapping, named by their Enterprise
Integration Pattern (Hohpe and Woolf, 2003). The Bridge owns the stages; the
adapter contributes data to them through these terms.

| stage | Enterprise Integration Pattern | the adapter contributes |
|---|---|---|
| read and chunk | **Splitter** | `bridge:elementNameOfEachRecord`, `bridge:jsonPathOfEachRecord` |
| transform | **Message Translator** | `bridge:mapping`, `bridge:table` |
| Cascade RDF as target | **Canonical Data Model** | `bridge:vocabulary`, `bridge:cascadeVocabularyPin`, `bridge:vocabularyFile` |
| link records | **Aggregator** | `bridge:documentTableQuery`: a link within one source record is a name the mapping mints, and to any other record, in the document or not, that record's computed name |
| name versions, write arrivals | **Message History** | each version, linked to its record by `prov:specializationOf`, and the source's version metadata on its arrival |
| check, validate | **Message Validator** | `bridge:sourceSchema`, `bridge:documentSchema` |
| findings | **Invalid Message Channel** | `bridge:findingsQuery` |
| re-import as no-op | **Idempotent Receiver** | nothing: a pod writer's re-import checks (the same document, the same source version, the same version as the current one) make it one |
| vendor quirks | **Normalizer** | a normalising pass per vendor, where the format has vendors |

- **Validation reports; it never refuses.** A source record that fails its
  schema is a finding, and the record still goes through.
- **`bridge:detectQuery` reports; it never routes.** A Bridge runs every source
  record whatever it answers. Choosing among adapters is the caller's, holding
  that answer.
- **A schema's `xs:include` and `xs:import` resolve against the schema's own
  IRI**, through the host, and only to files in the adapter package, except that
  an `xs:import` of the XML namespace (`http://www.w3.org/XML/1998/namespace`)
  or of XLink (`http://www.w3.org/1999/xlink`) whose `schemaLocation` is absent
  or names no file in the package, W3C's own address included, resolves to the
  Bridge's own copy of that W3C schema. Nothing is fetched.
- **A JSON Schema's IRI may carry a fragment**, a JSON Pointer
  ([RFC 6901](https://www.rfc-editor.org/rfc/rfc6901), fragment form): records
  are validated against the subschema it names, its `$ref`s resolved against
  the whole schema document. An XSD's IRI carries none.
- **A JSON Schema's `$ref` resolves as its draft says**, against the schema's
  `$id` or, where it declares none, its own IRI, and only within the schema or
  to files in the adapter package. Nothing is fetched.
- **A version's name is the Bridge's**, never the adapter's.
- **A Bridge's graph is a function of the document and the facts supplied with
  it**, and of nothing a pod holds.
- **A reference to a record not in the document is its computed name**, which
  resolves when that record arrives. Nothing is dropped.
- **A format has one adapter**, with vendor quirks as data, never one adapter per vendor.

Not settled: what Core contains.

## Versions

A mapping writes a record's version as an IRI with no fragment, the subject of
exactly one `prov:specializationOf`, whose object is the record's name, and each
node nested in the version as that IRI, `#` and a fragment built from the
node's position. The version's content is every triple whose subject is the
version or a node nested in it. It holds no blank node and names no other
version.

A Bridge names a version `ni:///sha-256;` and the unpadded base64url
([RFC 6920](https://www.rfc-editor.org/rfc/rfc6920)) of the SHA-256 of its
content's canonical N-Quads by RDFC-1.0, with `urn:cascade:this-version` in
place of the version's IRI, a nested node's IRI included. It hashes the content
as the mapping wrote it, before any store round trip, and writes the mapping's
graph with the version's name in place of its IRI in the same way. A Bridge must
reproduce the vectors in [`../fixtures/versioning/`](../fixtures/versioning/).

## Facts supplied with a document

A caller supplies facts about a document as a Turtle file, `convert`'s
`--facts` or an entry's `bridge:facts`, stating them of `bridge:thisDocument`
and `bridge:thisImport` as [`../shapes/facts.shapes.ttl`](../shapes/facts.shapes.ttl)
requires. A record's dataset holds them ([`sparql.md`](sparql.md#running-an-adapter)).

## What a Bridge writes after the mapping

A Bridge's graph for a document is the union of its records' graphs, each
version named, and:

- **the document**: its SHA-256 as its name, `a prov:Entity`, and every
  supplied fact, with that name in place of `bridge:thisDocument` and
  `bridge:serverBaseUrl` normalised;
- **the import**: a blank node, `a prov:Activity`, `prov:used` the document,
  every supplied fact with that node in place of `bridge:thisImport`, and a
  `prov:qualifiedAssociation` whose `prov:hadPlan` is a blank node `a
  prov:Plan` with the adapter's `identifier` as its `rdfs:label` and its
  `version` as its `pav:version`, and whose `prov:agent` is a blank node `a
  prov:SoftwareAgent` naming the Bridge's release by `rdfs:label` and
  `pav:version`;
- **each version's arrival**: one blank node carrying every triple the mapping
  wrote of a node it linked to that version by `bridge:arrivedAs`, and
  `bridge:arrivedAs` the version's name, `prov:wasDerivedFrom` the document,
  `prov:wasGeneratedBy` the import and, where the mapping wrote none,
  `bridge:selector` the `rdf:value` of the source record's selector. A mapping
  writes there the source's own version metadata: its version id as
  `pav:version`, a plain string, and when it was last updated as
  `pav:lastUpdateOn`, the source's text as written, an `xsd:date` where it states
  a date and an `xsd:dateTime` where it states a date-time. For a record it finds inside the source record, as a FHIR
  contained resource is, it writes there `bridge:selector` as the `rdf:value`
  of the selector that record would have as a source record of its own:
  `/entry/0/resource/contained/0` under `/entry/0`.

[`../fixtures/synthetic-adapter/fixtures/expected/example-0001.ttl`](../fixtures/synthetic-adapter/fixtures/expected/example-0001.ttl)
is a whole document's graph.
