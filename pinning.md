# Pinning

- **The specification names no adapter and no engine.** Every check is published
  from here as an action and runs in the adapter's or engine's own CI.
- **An adapter pins the specification** as `bridge:specPin` in its crate.
- **An engine pins the specification** in its `compatibility.json`.
- **An engine and an adapter pin each other only by saying so**, in a
  `compatibility.json` entry ([`compatibility.md`](compatibility.md)).
- **A pin moves in the pull request that needs the new revision**, never on a
  schedule, and that pull request re-measures what the pin measures.
- **The specification merges first.** A downstream pull request may pin its
  feature branch meanwhile, and swaps to the merge commit once it lands. Nothing
  waits on a tag.
- **At merge time a pin is a commit or tag on the counterpart's default branch,
  or that branch.** `ready` in [`compatibility.md`](compatibility.md) checks it.
- **Nothing pins what it does not consume.** An adapter names only the Cascade
  vocabularies it writes. This repository pins nothing.
