# Engine stages

The stages a Bridge runs around an adapter's mapping, named by their Enterprise
Integration Pattern (Hohpe and Woolf, 2003). The Bridge owns the stages; the
adapter contributes data to them through these terms.

| stage | Enterprise Integration Pattern | the adapter contributes |
|---|---|---|
| read and chunk | **Splitter** | `bridge:elementNameOfEachRecord`, `bridge:jsonPathOfEachRecord` |
| transform | **Message Translator** | `bridge:mapping`, `bridge:table` |
| Cascade RDF as target | **Canonical Data Model** | `bridge:vocabulary`, `bridge:cascadeVocabularyPin`, `bridge:vocabularyFile` |
| link within the batch | **Aggregator** | nothing: the mapping emits the links, the Bridge resolves them |
| name versions | **Message History** | each version, linked to its record by `prov:specializationOf` |
| check, validate | **Message Validator** | `bridge:sourceSchema`, `bridge:documentSchema` |
| findings | **Invalid Message Channel** | `bridge:findingsQuery` |
| re-import as no-op | **Idempotent Receiver** | nothing beyond a guarantee |
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
- **A JSON Schema's `$ref` resolves as its draft says**, against the schema's
  `$id` or, where it declares none, its own IRI, and only within the schema or
  to files in the adapter package. Nothing is fetched.
- **A version's name is the Bridge's**, never the adapter's.
- **Re-import changes nothing**: an adapter's output is a function of its input.
- **A format has one adapter**, with vendor quirks as data, never one adapter per vendor.

Not settled: what Core contains, and whether an output record points at another
output record of the same source record by a blank node the Bridge resolves or by a minted name.

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
