# bench — Agent Context

- **A generator is deterministic**: no unseeded randomness, no clock, no network.
- **A generator takes paths and learns no adapter's name.**
- **CI never runs a generator to make an input.** Its output is committed, gzipped where
  large, with its digests in the manifest and, in an adapter, in the crate. The crate's
  provenance names the generator at a commit.
- **A schema here is what every harness writes or reads**, so a change to it says why in
  its commit message.
