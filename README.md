# cascade-bridge-spec

The home of the **Cascade Bridge Specification**: the contract every Cascade
Bridge Adapter and every Cascade Bridge implementation follows.

Three proper nouns:

| term | what it is |
|---|---|
| **Cascade Bridge Specification** | the open standard: adapter package format, engine stages, profiles, the findings model, the fixture contract. This repository |
| **Cascade Bridge for `<language>`** | an implementation, once per language, conforming or not |
| **Cascade Bridge Adapter** | a data package for one format, authored by an integration engineer |

The Bridge depends on the Cascade runtime and the runtime never depends on the
Bridge. Format knowledge leaves the runtime and becomes data; the thing that
runs that data is a Bridge.

## Status: DRAFT

**No compatibility is promised before a numbered v1.** Every namespace here is
`v1-draft`. Terms may be renamed, cardinalities may change, and the profile IRI
does not dereference yet.

v1-draft specifies XML source formats and one mapping language, XSLT 3, as the
`xslt-3` profile. Other source formats and mapping languages are not specified
yet.

Nothing here has yet been executed by a Bridge, because no Bridge exists.

### What is normative here, and what is not settled

Normative — this repository is the authority, and an adapter that fails these is
not a conforming adapter package:

- the `bridge:` vocabulary, [`vocab/bridge.ttl`](vocab/bridge.ttl);
- the SHACL shapes, [`shapes/bridge.shapes.ttl`](shapes/bridge.shapes.ttl);
- the adapter profile, [`adapter/profile/ro-crate-metadata.json`](adapter/profile/ro-crate-metadata.json);
- the adapter manifest contract, [`adapter/ro-crate-metadata.md`](adapter/ro-crate-metadata.md);
- the test manifest contract, [`adapter/fixtures/manifest.md`](adapter/fixtures/manifest.md);
- the validation list, [`adapter/validation.md`](adapter/validation.md);
- the pinning rules, [`pinning.md`](pinning.md).

Not settled, and not answerable from anything in this repository. If one of these
blocks you, ask:

- **What Core contains**: what every Bridge must run, beneath the profiles an
  adapter requires. Until it is settled, only an adapter requiring no profile at
  all can be shown to need Core alone.
- **The canonical findings model.** One is wanted; the shape is not
  chosen. [`adapter/fixtures/README.md`](adapter/fixtures/README.md)
  states the two published candidates and the constraint keeping the question
  open.
- **Router precedence** when two adapters' detect rules both match a document.
- **The export direction.** Import only is specified; `out/` is not.

Where a document here touches one of these, it says so.

## Start here

The specification exists so two things can be built. Start at the one you are
building; its entry point names what it needs from the other.

| you are building | start at | what it covers |
|---|---|---|
| **an adapter** — a data package for one source format | [`adapter/`](adapter/) | the crate, fixtures, the test manifest, and the six checks your package must pass |
| **an engine** — a Bridge, the thing that runs adapters | [`engine/`](engine/) | the stages you run around a mapping, and how you execute an adapter's test manifest |

Building an adapter, you also need [`pinning.md`](pinning.md): how an adapter
names the revision of this specification it is built against.

## Layout

```
adapter/                       building an adapter: its crate, fixtures, test manifest, validation
adapter/profile/               the RO-Crate 1.2 Profile Crate an adapter names in conformsTo
engine/                        building an engine: stages, executing a test manifest
pinning.md                     how the three sides name the revisions they were built against
vocab/bridge.ttl               the bridge: vocabulary: adapter terms, and test terms on top of W3C's mf:
shapes/bridge.shapes.ttl       SHACL shapes for an adapter's crate and its test manifest, as one graph
scripts/validate-adapter.py    the adapter lint: the six checks of adapter/validation.md
scripts/selftest-lint.py       the mutation cases that show each check failing
fixtures/synthetic-adapter/    a synthetic adapter package: the lint's own test subject
.github/actions/validate-adapter/  the lint published as an action, which an adapter's CI calls
.github/workflows/validate.yml CI: this repository's own files, and nothing else's
```

## How an adapter declares conformance

An adapter package is an RO-Crate 1.2 whose root entity is the adapter. Two
properties on that root entity declare conformance to this specification:

```jsonc
"conformsTo": [
  { "@id": "https://ns.cascadeprotocol.org/bridge/v1-draft/adapter-profile/" }
],
"bridge:specPin": {
  "@id": "https://github.com/jayostis/cascade-bridge-spec/commit/<full SHA>"
}
```

`conformsTo` names *which contract*; `bridge:specPin` names *which revision of
it*, as a `SoftwareSourceCode` entity in the crate carrying `codeRepository` and
`version` (the full SHA) — the same shape `bridge:vocabularyPin` uses.

**The profile IRI does not dereference yet.** Nothing is published at
`https://ns.cascadeprotocol.org/bridge/v1-draft/adapter-profile/`. It is an
identifier, and the Profile Crate that describes it is
[`adapter/profile/ro-crate-metadata.json`](adapter/profile/ro-crate-metadata.json) in this
repository. The full field-by-field contract is
[`adapter/ro-crate-metadata.md`](adapter/ro-crate-metadata.md).

## How to validate an adapter

```bash
python3 -m pip install pyshacl rdflib roc-validator lxml
python3 scripts/validate-adapter.py <path to an adapter checkout>
```

That runs the six checks a conforming adapter package must pass — the crate, the
shapes, the file inventory, the digests, the inputs against their schemas and the
expected graphs. What each one is, and what a failure means, is
[`adapter/validation.md`](adapter/validation.md); it is the authority and this is not a
second copy of it. Exit status is 0 when the run passes.

**Every check says whether it ran.** `ok`, `nothing to check` and `not run` are
three different sentences: a lint that silently checks nothing is worse than no
lint.

An adapter does not run that by hand. The same checks are published from this
repository as a composite GitHub Action, and an adapter's whole CI is the two
lines in [`adapter/validation.md`](adapter/validation.md). The ref in
the second is the adapter's `bridge:specPin` in executable form: the two name
the same commit of this repository, and the action checks that they do. The
action takes a directory, names no adapter, and clones nothing but the caller's
own checkout — the arrow runs from adapter to specification.

[`adapter/validation.md`](adapter/validation.md) has the full six-item list a
conforming package must pass, the words a check may be reported in, and the
media types an adapter package may declare.
[`fixtures/README.md`](fixtures/README.md) is the synthetic package the lint is
run against here, and `scripts/selftest-lint.py` is where each check is seen
failing.

## Alignment, in brief

The specification knows about itself. An adapter knows about the specification.
A Bridge knows about the specification. A catalogue knows about all of them and
nothing knows about it — and that catalogue is a repository of its own, which
does not exist yet. **Nothing here names an adapter**, and this repository's CI
validates this repository's own files and no one else's.

Every dependency is a commit SHA, and every pinned SHA is tagged in the
repository it pins, because a branch tip is not a guarantee. An adapter's
`uses:` ref and its `bridge:specPin` name the same commit of this repository.
Pins move in the pull request that needs them, with the measurement re-run in
the same commit, never swept forward on a schedule and never synced to `main`.
Nothing pins what it does not consume — which is why this repository pins
nothing at all. A comparison is insensitive to everything the format does not
mean. And a Bridge's verdict on an adapter reaches a catalogue as an EARL
report, never as a pin in either direction.

The reasoning is in [`pinning.md`](pinning.md).

## Licence

Apache-2.0.
