# Engine stages

The stages a Bridge runs around an adapter's mapping, named by their Enterprise
Integration Pattern (Hohpe and Woolf, 2003). The Bridge owns the stages; the
adapter contributes data to them through these terms.

| stage | Enterprise Integration Pattern | the adapter contributes |
|---|---|---|
| read and chunk | **Splitter** | `bridge:elementNameOfEachRecord` |
| transform | **Message Translator** | `bridge:mapping`, `bridge:table` |
| Cascade RDF as target | **Canonical Data Model** | `bridge:vocabulary`, `bridge:cascadeVocabularyPin` |
| link within the batch | **Aggregator** | nothing: the mapping emits the links, the Bridge resolves them |
| stamp | **Message History** | `bridge:stampPredicate`; it receives the stamp |
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
  IRI**, through the host, and only to files in the adapter package. Nothing is
  fetched.
- **The stamp is the Bridge's**, never the adapter's.
- **Re-import changes nothing**: an adapter's output is a function of its input.
- **A format has one adapter**, with vendor quirks as data, never one adapter per vendor.

Not settled: what Core contains, and whether an output record points at another
output record of the same source record by a blank node the Bridge resolves or by a minted name.
