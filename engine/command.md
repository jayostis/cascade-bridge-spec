# The commands an engine offers

Both, not either.

## `test`

```
test <adapter directory> [--earl <file>] [--datasets]
```

It executes the adapter's test manifest ([`executing.md`](executing.md)) and,
with `--earl`, writes the EARL report in Turtle to `<file>`. With `--datasets` it
also streams the datasets of `bridge:DatasetCompletionTest` entries; without it,
those entries are reported without being run.

**The exit code means nothing to the tooling; the report does.** A run that wrote
no report does not hold.

An engine states how to run it in its `compatibility.json`
([`../compatibility.md`](../compatibility.md)): `setup` and `command` as argument
vectors, and the tooling appends `test`, the adapter directory, `--earl` and the
report file to `command`.

## `convert`

```
convert <adapter directory> <document> [--out <file>] [--format turtle|ntriples]
```

It runs the adapter over every record of `<document>`, a source document the
caller holds rather than one the adapter committed, and emits their union as one
graph: Turtle by default, `--format ntriples` for a reader that consumes a
stream, on standard output unless `--out` names a file. Standard output carries
the graph and nothing else.

**`bridge:detectQuery` is reported, not enforced**: the engine converts a
document whose ASK answers false, and says so.
