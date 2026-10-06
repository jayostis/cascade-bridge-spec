# The library a Bridge offers

What a Bridge offers a program that loads it: five operations, bytes in and
bytes out. The cases in [`../fixtures/library/`](../fixtures/library/) pin
each, as `bridge:LibraryTest` in [`../vocab/bridge.ttl`](../vocab/bridge.ttl)
judges them.

## What the caller names

The caller gives every IRI, and none comes from where a file was found.

- **The adapter IRI** is the base the crate and its test manifest are read
  with: each file of the adapter is that IRI followed by its path, so each
  envelope and each test entry is named under it.
- **The vocabulary IRI** is what each `bridge:vocabularyFile` path resolves
  against.
- **The document IRI** is what a finding names as its `oa:hasSource`. The graph
  names the document by its SHA-256 ([`stages.md`](stages.md)), never by this.
- **The facts IRI** is the base the facts are read with.

An adapter's files are given as a map from the path its crate writes
(`in/example-record.rq`) to the file's bytes, and a vocabulary's as a map from
each `bridge:vocabularyFile` path.

## describe

From the bytes of an adapter's `ro-crate-metadata.json` and the adapter IRI
alone, a graph about the adapter IRI, `a bridge:Adapter`, in the format the
caller asks, Turtle or N-Triples, carrying the crate's own:
`schema:identifier`, `schema:version`, `bridge:sourceMediaType`, each
`bridge:envelope`, `bridge:cascadeVocabularyRepository` and each
`bridge:vocabularyFile`; and

- a `bridge:loadFile` for each file a load needs: the metadata file, and each
  file inside the adapter the root entity or one of its envelopes names by a
  `bridge:` term other than `bridge:testManifest`;
- a `bridge:crateFile` for each file a test needs: the metadata file, and each
  `File` entity of the crate inside the adapter.

Each is a path as a map keys it, without a fragment. Only the Bridge reads an
adapter's metadata: describe is how a host learns what to fetch.

## load

From an adapter's map and, where the caller gives one, a vocabulary's, a loaded
adapter. It reads nothing only a test needs: no test manifest and nothing under
`fixtures/`. A loaded adapter converts any number of documents, and no call
changes it.

## ask

Whether a loaded adapter accepts a document, given as its bytes, its IRI and
an optional envelope IRI, without converting it: `true` or `false`, the
`bridge:detectQuery`'s answer over the document's envelope skeleton
([`sparql.md`](sparql.md)).

## convert

From a loaded adapter, one whole document as its bytes and its IRI, the facts
supplied with it as Turtle and their IRI where the caller gives them, and an
optional envelope IRI, the graph and the findings, each as bytes in the format
the caller asks, Turtle or N-Triples.

The graph is every record of the document, emitted as one. The findings are
the union of every record's, the ones a `bridge:expectedFindings` file is
compared against, and never change the graph.

The document is read in the envelope the caller names, whether or not it
admits the document ([`sparql.md`](sparql.md)), as `test` reads an entry's
input in the envelope the entry names, and a Bridge refuses nothing for it.
Without one, it is read in the envelope
that admits it, a JSON envelope naming a `bridge:docRootMemberValue` before one
naming none; where that leaves more than one, or none, which is used is not
specified. Without facts, the document is converted with none
([`stages.md`](stages.md#facts-supplied-with-a-document)).

On an adapter naming a `bridge:vocabularyFile`, loaded with no vocabulary,
convert returns the graph without validating it against those files, no
findings, and says so.

## test

From the same maps as load, the EARL report in Turtle that
[`executing.md`](executing.md) describes. It is for conformance only. Its
`bridge:DatasetCompletionTest` entries are `earl:untested`. On an adapter
naming a `bridge:vocabularyFile`, given no vocabulary, it fails with
`bridge:vocabularyFailure`.

## Failures

A call that fails says which kind of failure it is, each a `bridge:FailureKind`
in [`../vocab/bridge.ttl`](../vocab/bridge.ttl):

| kind | what failed |
|---|---|
| `bridge:documentFailure` | the document, or an envelope IRI naming no envelope the adapter declares |
| `bridge:factsFailure` | the facts supplied with the document |
| `bridge:adapterFailure` | the adapter, or a profile it requires that the Bridge does not offer |
| `bridge:vocabularyFailure` | the vocabulary |
| `bridge:fileMissingFailure` | a file a map lacks, which it names by the map and the path, so a host can fetch it and call again |
| `bridge:bridgeFailure` | the Bridge itself |

A file missing from a map under test is a `bridge:fileMissingFailure`, not an
`earl:failed` entry. Findings are data, never failures.

After a `bridge:bridgeFailure`, that loaded adapter is thrown away and the
adapter loaded again: one bad document never spoils the conversions after it.
Any other failure leaves the loaded adapter as it was.
