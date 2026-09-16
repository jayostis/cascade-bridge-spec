# Engine stages, in the vocabulary integration engines already use

The stages a Bridge runs *around* an adapter's mapping. Each is an established
Enterprise Integration Pattern (Hohpe and Woolf, 2003), so the design reads in
the terms every integration engine, Apache Camel included, already documents.
Nothing here is invented, and nothing here is a name a Bridge implementer has to
learn twice.

The division of labour: **the Bridge owns the stages, the adapter contributes
data to them.** The third column names the terms it contributes through; what
each one is, is its `rdfs:comment` in
[`../vocab/bridge.ttl`](../vocab/bridge.ttl).

| stage | Enterprise Integration Pattern | the adapter contributes |
|---|---|---|
| read and chunk | **Splitter** | `bridge:unit` |
| detect and route | **Content-Based Router** | `bridge:detectQuery` |
| transform | **Message Translator** | `bridge:mapping`, `bridge:table` |
| Cascade RDF as target | **Canonical Data Model** | `bridge:vocabulary`, `bridge:vocabularyPin` |
| link within the batch | **Aggregator** | nothing; the mapping emits the links and the Bridge resolves them within one import |
| stamp | **Message History** | `bridge:ignorePredicate`, and nothing else: it *receives* the stamp |
| check, validate | **Message Validator**, findings to an **Invalid Message Channel** | `bridge:sourceSchema`, `bridge:documentSchema` |
| findings | **Dead Letter Channel** / **Invalid Message Channel** | `bridge:findingsQuery`, and the sidecar beside each expected graph |
| re-import as no-op | **Idempotent Receiver** | nothing beyond a guarantee |
| vendor quirks | **Normalizer** | a normalising pass per vendor, where the format has vendors |

## Four the pattern name does not settle

**Validation reports; it never refuses and never destroys.** A unit that fails
its schema is a finding about the input, and the unit still goes through. An
adapter can flag; it cannot reject. Everything that produces a finding — source
validation, the mapping, the undeclared-predicate check, SHACL — lands in one
findings model, whose shape is still open
([`../adapter/fixtures/README.md`](../adapter/fixtures/README.md)).

**The stamp is the Bridge's, not the adapter's**, which is what
`bridge:ignorePredicate` exists for: an oracle carries whatever produced it, a
Bridge writes its own, and both sides' come off before judging. An adapter that
stamped provenance itself would be doing the Bridge's job and would fail its own
fixtures on a second Bridge.

**Re-import must change nothing.** The adapter owes only that everything it
emits is a function of the input, which a declarative mapping gives by
construction. The naming rule that makes re-import a no-op is the Bridge's.

**A format has one adapter, with vendor quirks on the source side**, never one
adapter per vendor. A quirk profile is data in the package like everything else,
and a format with one publisher declares none.

Two questions these stages raise are open, and nothing here answers them: what
Core contains beneath the profiles an adapter requires, and how a record points
at another record of the same unit — a blank node the Bridge resolves, or a
minted name. An adapter's layout must not depend on the second.
