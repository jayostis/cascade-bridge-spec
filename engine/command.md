# The commands an engine offers

All three, not some. `test` and `convert` are callers of the library, and
[`library.md`](library.md) says what each does. Each names the adapter and the
vocabulary by their directories' `file:` IRIs, and the document and its facts
by their own, and reads a directory's files into that directory's map.

An engine states how to run it in its `compatibility.json`
([`../compatibility.md`](../compatibility.md)): a `setup` and a `command` for
each host, as argument vectors, and the tooling appends a command and its
arguments to each host's `command`.

## `test`

```
test <adapter directory> [--earl <file>] [--datasets] [--vocabularies <directory>]
```

The library's `test`. `<adapter directory>` is the adapter's map and
`--vocabularies` the vocabulary's: a checkout of the repository the adapter's
`bridge:cascadeVocabularyPin` names, at the version the run picked
([`../compatibility.md`](../compatibility.md)). `--earl` writes the report to
`<file>`. With `--datasets` the command also streams the datasets of
`bridge:DatasetCompletionTest` entries.

**The exit code means nothing to the tooling; the report does.** A run that wrote
no report does not hold. The tooling appends `test`, the adapter directory,
`--earl` and the report file, and `--vocabularies` and the checkout it picked.

## `convert`

```
convert <adapter directory> <document> [--envelope <iri>] [--facts <file>] [--out <file>] [--findings <file>] [--format turtle|ntriples] [--vocabularies <directory>]
```

The library's `convert`, on the adapter loaded from `<adapter directory>` and,
with `--vocabularies`, a checkout of the repository its
`bridge:cascadeVocabularyPin` names, at the commit it pins. `<document>` is
the document, a file the caller holds rather than one the adapter committed.
`--envelope` is the envelope IRI, resolved against the adapter's
`ro-crate-metadata.json`, so `#envelope-set` names the envelope that file
declares as `#envelope-set`. `--facts` is a Turtle file of the facts.
`--format` is the format, Turtle when it is not given.

The graph goes to `--out`, or to standard output, which carries the graph and
nothing else. The findings go to `--findings` and never to standard output;
where the library returns none, a run given `--findings` produces nothing.

**The exit code is the whole of what a caller learns**, because `convert` writes
no report: zero when the graph was produced, non-zero when it was not, and
standard output carries nothing in that case.

## `library`

```
library <calls file> <results directory>
```

For conformance only: the tooling runs the cases of
[`../fixtures/library/`](../fixtures/library/) through it, appending
`library`, the calls file it wrote and an empty results directory. It makes
each call the calls file lists on the library and writes what each returned.
It judges nothing.

### The calls file

JSON, as [`library-calls.schema.json`](library-calls.schema.json) says:
`cases`, each a `name` and its `calls`, in the order they are made. A call is
an object of one member, named for the operation:

| member | its value |
|---|---|
| `describe` | `adapter`, the adapter IRI; `metadata`, the path of its `ro-crate-metadata.json`; `format` |
| `load` | `adapter`, a map, and `vocabulary`, a map, where the call gives one |
| `ask` | `document` |
| `convert` | `document` and `format` |
| `test` | `adapter` and `vocabulary`, as `load` takes them |

- A map is `iri`, its IRI, and `files`, an object from each key to the path of
  the file whose bytes the map holds under that key. It holds those files and
  no other.
- A `document` is `iri` and `path`, and, where the call gives them,
  `envelope`, the envelope IRI, and `facts`, an `iri` and a `path`.
- `format` is `turtle` or `ntriples`.
- Every path is absolute.

`ask` and `convert` are made on the adapter the latest `load` before them in
their case that did not fail returned. Where there is none, the call is not
made and nothing is written for it. After a `bridge:bridgeFailure`, the next
call of the case is made on the adapter loaded again from that `load`'s maps.

### The results directory

For the call at position *n* of a case, counting from 1, the command writes
into `<results directory>/<case name>/`:

- `<n>.json`, as [`library-result.schema.json`](library-result.schema.json)
  says: `{"failure": {"kind": …}}` where the call failed, `kind` the local
  name of its `bridge:FailureKind`, with `map`, `adapter` or `vocabulary`, and
  `path` for a `fileMissingFailure`, and an optional `message`; otherwise
  `{"answer": true}` or `{"answer": false}` for `ask`, and `{}` for any other
  call;
- `<n>.graph`, the graph `describe` or `convert` returned, as returned;
- `<n>.findings`, the findings `convert` returned, where it returned any;
- `<n>.report`, the report `test` returned, as returned.

**The exit code means nothing to the tooling; the results do.** A call with no
result does not hold.
