# The commands an engine offers

Both, not either.

## `test`

```
test <adapter directory> [--earl <file>] [--datasets] [--vocabularies <directory>]
```

It executes the adapter's test manifest ([`executing.md`](executing.md)) and,
with `--earl`, writes the EARL report in Turtle to `<file>`. With `--datasets` it
also streams the datasets of `bridge:DatasetCompletionTest` entries; without it,
those entries are reported without being run.

`--vocabularies` names a checkout of the repository the adapter's
`bridge:cascadeVocabularyPin` names, at the version the run picked
([`../compatibility.md`](../compatibility.md)), where each of its
`bridge:vocabularyFile` paths is read from.

**The exit code means nothing to the tooling; the report does.** A run that wrote
no report does not hold.

An engine states how to run it in its `compatibility.json`
([`../compatibility.md`](../compatibility.md)): a `setup` and a `command` for each
host, as argument vectors, and the tooling appends `test`, the adapter directory,
`--earl` and the report file, and `--vocabularies` and the checkout it picked, to
each host's `command`.

## `convert`

```
convert <adapter directory> <document> [--out <file>] [--findings <file>] [--format turtle|ntriples] [--vocabularies <directory>]
```

It runs the adapter over every record of `<document>`, a source document the
caller holds rather than one the adapter committed, and emits their union as one
graph: Turtle by default, `--format ntriples` for a reader that consumes a
stream, on standard output unless `--out` names a file. Standard output carries
the graph and nothing else.

`--findings` writes the union of every record's findings as one graph, in the
same format, to `<file>` and never on standard output. They are the findings a
`bridge:expectedFindings` file is compared against. It never changes the graph.

`--vocabularies` names a checkout of the repository the adapter's
`bridge:cascadeVocabularyPin` names, at the commit it pins, where each of its
`bridge:vocabularyFile` paths is read from. Without it, on an adapter naming a
`bridge:vocabularyFile`, a run writes the graph without validating it against
those files, and one given `--findings` produces nothing.

**The exit code is the whole of what a caller learns**, because `convert` writes
no report: zero when the graph was produced, non-zero when it was not, and
standard output carries nothing in that case.
