# Engine stages

The stages a Bridge runs around an adapter's mapping, each named as the
Enterprise Integration Pattern (Hohpe and Woolf, 2003) it already is, so the
design reads in terms every integration engine documents. **The Bridge owns the
stages; the adapter contributes data to them**, through the terms in the last
column.

| stage | Enterprise Integration Pattern | the adapter contributes |
|---|---|---|
| read and chunk | **Splitter** | `bridge:unit` |
| detect and route | **Content-Based Router** | `bridge:detectQuery` |
| transform | **Message Translator** | `bridge:mapping`, `bridge:table` |
| Cascade RDF as target | **Canonical Data Model** | `bridge:vocabulary`, `bridge:vocabularyPin` |
| link within the batch | **Aggregator** | nothing: the mapping emits the links, the Bridge resolves them |
| stamp | **Message History** | `bridge:ignorePredicate`; it receives the stamp |
| check, validate | **Message Validator** | `bridge:sourceSchema`, `bridge:documentSchema` |
| findings | **Invalid Message Channel** | `bridge:findingsQuery` |
| re-import as no-op | **Idempotent Receiver** | nothing beyond a guarantee |
| vendor quirks | **Normalizer** | a normalising pass per vendor, where the format has vendors |

## What the pattern names do not settle

**Validation reports; it never refuses.** A unit that fails its schema is a
finding, and the unit still goes through. Every finding, from any stage, lands in
one findings model, which is not settled
([`../adapter/fixtures/README.md`](../adapter/fixtures/README.md)).

**The stamp is the Bridge's.** An adapter that stamped provenance itself would
fail its own fixtures on a second Bridge.

**Re-import changes nothing.** The adapter owes only that its output is a
function of its input, which a declarative mapping gives by construction.

**A format has one adapter**, with vendor quirks as data on the source side,
never one adapter per vendor.

Not settled: what Core contains, and whether a record points at another record of
the same unit by a blank node the Bridge resolves or by a minted name. An
adapter's layout must not depend on the answer.
