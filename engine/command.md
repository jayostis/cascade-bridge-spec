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
no crate to carry its spec pin. Its keys, their types and their cardinalities are
the engine's form in [`../compatibility.md`](../compatibility.md); what an engine
puts in them is the build it already has, as an argument vector rather than a
shell line:

```jsonc
"setup":   ["cargo", "build", "--release", "-p", "cascade-bridge-cli"],
"command": ["cargo", "run", "--release", "-p", "cascade-bridge-cli", "--"]
```

The tooling appends `test`, the adapter directory, `--earl` and the report file
to `command`, so what it runs is the command above.
