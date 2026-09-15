# The command an engine offers

What an engine owes the tooling that tests it against adapters, in its own CI and
in an adapter's. It is the whole of what
[`../scripts/compatibility.py`](../scripts/compatibility.py) needs from an engine.

## `test`

An engine offers the command

```
test <adapter directory> [--earl <file>] [--datasets]
```

It executes the test manifest of the adapter in `<adapter directory>` as
[`executing.md`](executing.md) says, and with `--earl` writes the EARL report,
in Turtle, to `<file>`. With `--datasets` it also streams the datasets of
`bridge:DatasetCompletionTest` entries; without it, those entries are reported
without being run.

**Its exit code carries no meaning the tooling relies on; the report does.** An
entry's outcome is read from the report, and a run that wrote no report is
judged as not holding ([`../compatibility.md`](../compatibility.md)).

## `compatibility.json`

An engine commits a `compatibility.json` at its repository root, because it has
no crate to carry its spec pin. It carries, in the engine's form
[`../compatibility.md`](../compatibility.md) defines:

- **`specification`**, the revision of this specification the engine is
  written against;
- **`setup`**, the argument vector that prepares the engine in a fresh checkout
  (`["npm", "ci"]`, `["cargo", "build", "--release", "-p", "cascade-bridge-cli"]`);
- **`command`**, the argument vector the tooling appends
  `test <adapter directory> --earl <file>` to
  (`["node", "packages/bridge-cli/src/cli.ts"]`,
  `["cargo", "run", "--release", "-p", "cascade-bridge-cli", "--"]`).

Both vectors run without a shell, with the engine's checkout as the working
directory, so one file works on Windows and on Linux CI. The toolchain they
name is the engine's to provide in its own CI; this specification learns no
language's build.

`testedWith` is optional: an engine lists an adapter only to assert that it
passes it.
