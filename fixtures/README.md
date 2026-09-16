# Fixtures

The subjects this repository's machinery runs against.

```
synthetic-adapter/   an adapter package: the adapter profile's test subject
fake-engine/         an engine that honours engine/command.md and runs nothing
lift/                the vectors a sparql-1.1 Bridge must reproduce (engine/sparql.md)
```

**All of them are invented.** This repository must not know that any real
adapter or engine exists ([`../pinning.md`](../pinning.md)), and a real one here,
as a submodule, a clone or a name in a workflow, is that bug wearing a fixture's
clothes. The published tooling still has to be exercised, so it runs against
subjects this repository owns.

Editing a digested file in `synthetic-adapter/` means restating its `sha256` and
`contentSize` in the crate, in the same commit.
