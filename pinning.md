# Pinning

- **The specification names no adapter and no engine.** Every check is published
  from here as an action and runs in the adapter's or engine's own CI.
- **Nothing pins the specification, an engine or an adapter**
  ([`compatibility.md`](compatibility.md)).
- **Nothing pins what it does not consume.** An adapter names only the Cascade
  vocabularies it writes.
