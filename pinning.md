# Pinning

- **The specification names no adapter and no engine.** Every check is published
  from here as an action and runs in the adapter's or engine's own CI.
- **Nothing pins the specification, an engine or an adapter.** A run picks which
  version of each it uses when it starts ([`compatibility.md`](compatibility.md)).
- **An adapter pins `the-cascade-protocol/spec`** as `bridge:cascadeVocabularyPin`
  in its crate.
- **Nothing pins what it does not consume.** An adapter names only the Cascade
  vocabularies it writes.
