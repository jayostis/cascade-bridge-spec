# cascade-bridge-spec

The home of the **Cascade Bridge Specification**: the contract every Cascade
Bridge Adapter and every Cascade Bridge implementation follows.

Three proper nouns:

| term | what it is |
|---|---|
| **Cascade Bridge Specification** | the open standard: adapter package format, engine stages, profiles and tiers, the findings model, the fixture contract, the Bridge's obligations to the runtime. This repository |
| **Cascade Bridge for `<language>`** | an implementation, once per language, conforming or not |
| **Cascade Bridge Adapter** | a data package for one format, authored by an integration engineer |

The Bridge depends on the Cascade runtime and the runtime never depends on the
Bridge. Format knowledge leaves the runtime and becomes data; the thing that
runs that data is a Bridge.

## Status: DRAFT

**No compatibility is promised before a numbered v1.** Every namespace here is
`v1-draft`. Terms may be renamed, cardinalities may change, and the profile IRI
does not dereference yet.

Nothing here has yet been executed by a Bridge, because no Bridge exists.

### What is normative here, and what is not settled

Normative — this repository is the authority, and an adapter that fails these is
not a conforming adapter package:

- the `bridge:` vocabulary, [`vocab/bridge.ttl`](vocab/bridge.ttl);
- the SHACL shapes, [`shapes/bridge.shapes.ttl`](shapes/bridge.shapes.ttl);
- the adapter profile, [`profile/ro-crate-metadata.json`](profile/ro-crate-metadata.json);
- the adapter manifest contract, [`docs/adapter/manifest.md`](docs/adapter/manifest.md);
- the test manifest contract, [`docs/adapter/test-manifest.md`](docs/adapter/test-manifest.md);
- the validation list, [`docs/adapter/validation.md`](docs/adapter/validation.md);
- the pinning rules, [`docs/pinning.md`](docs/pinning.md).

Not settled, and not answerable from anything in this repository. If one of these
blocks you, ask:

- **What Core contains.** The open proposal is SPARQL CONSTRUCT over a generic
  lift as Core, with XSLT 3, RML and FHIR Mapping Language as optional profiles.
  Until it is settled, only an adapter requiring no profile at all can be shown
  to need Core alone.
- **The canonical findings model.** One is wanted; the shape is not
  chosen. [`docs/adapter/fixtures.md`](docs/adapter/fixtures.md)
  states the two published candidates and the constraint keeping the question
  open.
- **Router precedence** when two adapters' detect rules both match a document.
- **The export direction.** Import only is specified; `out/` is not.

Where a document here touches one of these, it says so.

## Start here

The specification exists so two things can be built. Pick one; you do not need
the other.

| you are building | start at | what it covers |
|---|---|---|
| **an adapter** — a data package for one source format | [`docs/adapter/`](docs/adapter/) | the crate, fixtures, the test manifest, and the six checks your package must pass |
| **an engine** — a Bridge, the thing that runs adapters | [`docs/engine/`](docs/engine/) | the stages you run around a mapping, and how you execute an adapter's test manifest |

[`docs/pinning.md`](docs/pinning.md) is short and both need it: how each side
names the revision of this specification it was built against.

## Layout

```
vocab/bridge.ttl               the bridge: vocabulary: adapter terms, and test terms on top of W3C's mf:
shapes/bridge.shapes.ttl       SHACL shapes for an adapter's crate and its test manifest, as one graph
profile/ro-crate-metadata.json the RO-Crate 1.2 Profile Crate an adapter names in conformsTo
docs/adapter/                  building an adapter: manifest, fixtures, test manifest, validation
docs/engine/                   building an engine: stages, executing a test manifest
docs/pinning.md                how the three sides name the revisions they were built against
scripts/validate-adapter.py    the adapter lint: the six checks of docs/adapter/validation.md
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
[`profile/ro-crate-metadata.json`](profile/ro-crate-metadata.json) in this
repository. The full field-by-field contract is
[`docs/adapter/manifest.md`](docs/adapter/manifest.md).

## How to validate an adapter

```bash
python3 -m pip install pyshacl rdflib roc-validator lxml
python3 scripts/validate-adapter.py <path to an adapter checkout>
```

That runs the six checks a conforming adapter package must pass — the crate, the
shapes, the file inventory, the digests, the inputs against their schemas and the
expected graphs. What each one is, and what a failure means, is
[`docs/adapter/validation.md`](docs/adapter/validation.md); it is the authority and this is not a
second copy of it. Exit status is 0 when all six pass, and nothing reaches the
network, so the run works offline and needs no credentials.

**Every check says whether it ran.** `ok`, `nothing to check` and `not run` are
three different sentences: a lint that silently checks nothing is worse than no
lint.

An adapter does not run that by hand. The same checks are published from this
repository as a composite GitHub Action, and an adapter's whole CI is the two
lines in [`docs/adapter/validation.md`](docs/adapter/validation.md). The ref in
the second is the adapter's `bridge:specPin` in executable form: the two name
the same commit of this repository, and the action checks that they do. The
action takes a directory, names no adapter, and clones nothing but the caller's
own checkout — the arrow runs from adapter to specification.

[`docs/adapter/validation.md`](docs/adapter/validation.md) has the full six-item list a
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

The reasoning is in [`docs/pinning.md`](docs/pinning.md).

## Licence

Apache-2.0.
