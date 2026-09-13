# Engine stages, in the vocabulary integration engines already use

The stages a Bridge runs *around* an adapter's mapping. Each is an established
Enterprise Integration Pattern (Hohpe and Woolf, 2003), so the design reads in
the terms every integration engine, Apache Camel included, already documents.
Nothing here is invented, and nothing here is a name a Bridge implementer has to
learn twice.

The division of labour the table states: **the Bridge owns the stages, the
adapter contributes data to them.** The third column says what an adapter
contributes to each, with the pilot adapter for ClinVar VCV XML as the worked
example rather than as the subject.

| stage | Enterprise Integration Pattern | what an adapter contributes |
|---|---|---|
| read and chunk | **Splitter** | the unit to split on: `bridge:unit` on the crate's root entity. ClinVar: `VariationArchive` |
| detect and route | **Content-Based Router** | the detect rule, as one XPath 3.1 boolean: `bridge:detectXPath`. ClinVar: `exists(/(ClinVarResult-Set\|ClinVarVariationRelease)/VariationArchive)` |
| transform | **Message Translator** | the mapping, in a language the adapter's required profiles name. ClinVar: XSLT 3, one module per record class |
| Cascade RDF as target | **Canonical Data Model** | the vocabularies it writes and the revision they are pinned at: `bridge:vocabulary`, `bridge:vocabularyPin` |
| link within the batch | **Aggregator** | the links between records of one unit, emitted by the mapping and resolved by the Bridge within one import. ClinVar: interpretation (RCV) and submitter-assertion (SCV) records point at their Variant |
| stamp | **Message History** | nothing; it *receives* the stamp. The adapter names the stamp predicates its test manifest ignores when comparing (`bridge:ignorePredicate`) |
| check, validate | **Message Validator**, findings to an **Invalid Message Channel** | the source-side schema every unit is validated against: `bridge:sourceSchema`, and a `bridge:documentSchema` per envelope where the source schema does not declare that root |
| findings | **Dead Letter Channel** / **Invalid Message Channel** | the expected contents of that channel, as the findings sidecar beside each expected graph |
| re-import as no-op | **Idempotent Receiver** | nothing beyond a guarantee: everything the adapter emits is a function of the input |
| vendor quirks | **Normalizer** | a normalisation pass per vendor, where the format has vendors. ClinVar has one publisher and no vendor dialects, so the pilot has none and declares none |

## Notes on the mapping to patterns

**Splitter.** A document is an envelope around one or more units. The Bridge
opens the envelope, splits on the unit, and hands the mapping one unit at a time
with its raw bytes preserved. Where the unit is a globally declared element in
the source schema, a unit validates on its own, and the Bridge need not validate
a multi-gigabyte release as a single document — which is what makes a dataset
completion test ([`../adapter/fixtures/manifest.md`](../adapter/fixtures/manifest.md)) runnable at all.

**Content-Based Router.** One XPath 3.1 expression, evaluated with the document
node as the context item. An adapter declares only the roots its publisher
publishes today; a document in another shape is routed elsewhere or reported,
never guessed at. The pilot's rule is narrower than the existing converter's
detector, which matches five roots — three belonging to older or different
ClinVar shapes, one being the bare unit — and misses the release envelope
entirely; narrowing it is a decision, and the adapter records which roots were
dropped and why.

**Message Translator and Canonical Data Model.** The mapping is the only
format-specific thing that runs, and it runs inside an engine the Bridge already
ships. What that engine is, is exactly what profiles are for: v1-draft specifies
one, `xslt-3`, and what Core contains is not settled. The target is Cascade RDF
in the pinned vocabularies, which is the canonical model every adapter writes to
and nothing else reads from an adapter.

**Aggregator.** One unit yields several records that point at each other. How the
pointer is expressed — a blank node the Bridge resolves, or a minted name — is an
identity question, not settled here, and the pattern is the same either way. An
adapter's layout must not depend on the answer, and the pilot's does not.

**Message History.** The stamp is the Bridge's, not the adapter's. This is why a
test manifest declares `bridge:ignorePredicate`: an oracle produced by an
existing converter carries that converter's stamps, a Bridge writes its own, and
the comparison removes both sides' before judging. An adapter that stamped
provenance itself would be doing the Bridge's job and would fail its own
fixtures on a second Bridge.

**Message Validator and Invalid Message Channel.** Validation reports; it never
refuses and never destroys. A unit that fails its schema is a finding about the
input, and the unit still goes through.
An adapter can flag; it cannot reject. Findings from source validation, the
mapping, the undeclared-predicate check and SHACL all land in the Bridge's one
findings model, whose standard shape is still open
([`../adapter/fixtures/README.md`](../adapter/fixtures/README.md)).

**Idempotent Receiver.** Importing the same document twice must change nothing.
The adapter's obligation is only that everything it emits is a function of the
input — which a declarative mapping guarantees by construction — and the naming
rule that makes re-import a no-op belongs to the Bridge.

**Normalizer.** Formats with several publishers need a normalising pass per
vendor before the translator: C-CDA from Epic and Cerner, say,
and the runtime already carries such quirks as code today. A quirk profile is
data in the package like everything else, and there are no vendor adapters — a
format has one adapter, with vendor quirks on the source side. A format with one
publisher declares none.
