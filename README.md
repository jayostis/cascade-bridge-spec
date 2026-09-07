# cascade-bridge-spec

The home of the **Cascade Bridge Specification**: the contract every Cascade
Bridge Adapter and every Cascade Bridge implementation follows.

Three proper nouns, from section 2 of the Cascade Bridge RFC
([the-cascade-protocol/spec#43](https://github.com/the-cascade-protocol/spec/issues/43)):

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

This repository is **thin and pilot-driven**. Everything in it was seeded from
phase 1 of one adapter,
[cascade-bridge-adapter-clinvar](https://github.com/jayostis/cascade-bridge-adapter-clinvar),
and nothing in it has yet been executed by a Bridge, because no Bridge exists.
It was created now, rather than after the first engine, so that the phase 2
engine is written against a contract with its own home instead of against files
inside one adapter. A contract that lives inside the thing it constrains cannot
be disagreed with.

### What is normative here, and what is still discussed on spec#43

Normative — this repository is the authority, and an adapter that fails these is
not a conforming adapter package:

- the `bridge:` vocabulary, [`vocab/bridge.ttl`](vocab/bridge.ttl);
- the SHACL shapes, [`shapes/bridge.shapes.ttl`](shapes/bridge.shapes.ttl);
- the adapter profile, [`profile/ro-crate-metadata.json`](profile/ro-crate-metadata.json);
- the adapter manifest contract, [`docs/adapter-manifest.md`](docs/adapter-manifest.md);
- the test manifest contract, [`docs/test-manifest.md`](docs/test-manifest.md);
- the validation list, [`docs/validation.md`](docs/validation.md);
- the alignment rules, [`docs/alignment.md`](docs/alignment.md).

Still open, and settled on spec#43 rather than here:

- **What Core contains.** RFC section 9 proposes SPARQL CONSTRUCT over a generic
  lift as Core, with XSLT 3, RML and FHIR Mapping Language as optional profiles,
  and marks it as question 1 for the spike. Until it is answered, only an adapter
  requiring no profile at all can be shown to need Core alone.
- **The canonical findings model.** RFC section 8 requires one; the shape is not
  chosen. [`docs/fixtures-and-provenance.md`](docs/fixtures-and-provenance.md)
  states the two published candidates and the constraint keeping the question
  open.
- **Router precedence** when two adapters' detect rules both match a document.
- **The export direction.** RFC section 6 puts an `out/` mapping in the package;
  the pilot is import-only, so nothing measured can be said about it yet.
- **Where the Bridge sits** relative to D-LAYERS-1's layers, and whether this
  full-separation repository layout is the right one at all (RFC sections 3 and
  15).

Where a document here touches an open question, it says so and links spec#43.

## Layout

```
README.md                      this file
LICENSE                        Apache-2.0
CLAUDE.md                      agent context: what is normative, the pinning rule, what to run
vocab/bridge.ttl               the bridge: vocabulary: adapter terms, and test terms on top of W3C's mf:
shapes/bridge.shapes.ttl       SHACL shapes for an adapter's crate and its test manifest, as one graph
profile/ro-crate-metadata.json the RO-Crate 1.2 Profile Crate an adapter names in conformsTo
scripts/validate-adapter.py    the adapter lint: all six checks of docs/validation.md
scripts/selftest-lint.py       the mutation cases that show each check failing
fixtures/synthetic-adapter/    a synthetic adapter package: the lint's own test subject
.github/actions/validate-adapter/  the lint published as an action, which an adapter's CI calls
docs/adapter-manifest.md       the adapter manifest contract
docs/test-manifest.md          the test manifest contract
docs/fixtures-and-provenance.md  committed inputs, referenced datasets, the findings sidecar
docs/stages.md                 the RFC's engine stages as Enterprise Integration Patterns
docs/validation.md             what a conforming adapter package must pass
docs/alignment.md              keeping spec, adapters and Bridges in step
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
[`docs/adapter-manifest.md`](docs/adapter-manifest.md).

## How to validate an adapter

```bash
python3 -m pip install pyshacl rdflib roc-validator lxml
python3 scripts/validate-adapter.py <path to an adapter checkout>
```

That runs the six checks a conforming adapter package must pass — the crate, the
shapes, the file inventory, the digests, the inputs against their schemas and the
expected graphs. What each one is, and what a failure means, is
[`docs/validation.md`](docs/validation.md); it is the authority and this is not a
second copy of it. Exit status is 0 when all six pass, and nothing reaches the
network, so the run works offline and needs no credentials.

**Every check says whether it ran.** `ok`, `nothing to check` and `not run` are
three different sentences: a lint that silently checks nothing is worse than no
lint.

An adapter does not run that by hand. The same checks are published from this
repository as a composite GitHub Action, so an adapter's whole CI is:

```yaml
      - uses: actions/checkout@v4
      - uses: jayostis/cascade-bridge-spec/.github/actions/validate-adapter@v0.3.0
```

The tag in that line is the adapter's `bridge:specPin` in executable form: the
two name the same commit of this repository, and the action checks that they do.
The action takes a directory, names no adapter, and clones nothing but the
caller's own checkout — the arrow runs from adapter to specification.

[`docs/validation.md`](docs/validation.md) has the full six-item list a
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

The reasoning, including the part inherited from
`conformance/scripts/SPEC_PIN`, is in [`docs/alignment.md`](docs/alignment.md).

## Related repositories

- [the-cascade-protocol/spec](https://github.com/the-cascade-protocol/spec) —
  the Cascade vocabularies and SHACL shapes an adapter writes to, the RFC this
  specification is drawn from ([#43](https://github.com/the-cascade-protocol/spec/issues/43)),
  and the identity RFC ([#38](https://github.com/the-cascade-protocol/spec/issues/38)).
- [the-cascade-protocol/conformance](https://github.com/the-cascade-protocol/conformance) —
  the fixture suite the pilot's oracles were copied from, and the source of the
  pinning discipline in `docs/alignment.md`.
- [the-cascade-protocol/cascade-cli](https://github.com/the-cascade-protocol/cascade-cli) —
  the runtime whose format converters an adapter re-expresses as data, and whose
  ClinVar conformance test is the comparison a test manifest restates.
- [jayostis/cascade-bridge-adapter-clinvar](https://github.com/jayostis/cascade-bridge-adapter-clinvar) —
  the pilot adapter every artefact here was seeded from, and the worked example
  the documents cite. Nothing a machine reads in this repository names it: it
  consumes this specification, not the other way round.
- `cascade-bridge-java`, `cascade-bridge-js` — the Bridges that will execute a
  test manifest, the JVM one as the ceiling and the JavaScript one as the floor
  (RFC section 16). **Neither exists yet**, and until one does, nothing in this
  specification has been run.

## Licence

Apache-2.0.
