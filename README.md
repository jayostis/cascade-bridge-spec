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

v1-draft specifies XML source formats and one mapping language, SPARQL 1.1
over a specified lift of the XML, as the `sparql-1.1` profile. Other source
formats and mapping languages are not specified yet.

### What is normative here, and what is not settled

Normative — this repository is the authority, and an adapter that fails these is
not a conforming adapter package:

- the `bridge:` vocabulary, [`vocab/bridge.ttl`](vocab/bridge.ttl);
- the SHACL shapes, [`shapes/bridge.shapes.ttl`](shapes/bridge.shapes.ttl);
- the adapter profile, [`adapter/profile/ro-crate-metadata.json`](adapter/profile/ro-crate-metadata.json);
- the adapter manifest contract, [`adapter/ro-crate-metadata.md`](adapter/ro-crate-metadata.md);
- the test manifest contract, [`adapter/fixtures/manifest.md`](adapter/fixtures/manifest.md);
- the validation list, [`adapter/validation.md`](adapter/validation.md);
- the command an engine offers, [`engine/command.md`](engine/command.md);
- the pinning rules, [`pinning.md`](pinning.md);
- the compatibility file, [`compatibility.md`](compatibility.md), and its
  context, [`vocab/compatibility.context.jsonld`](vocab/compatibility.context.jsonld).

Not settled, and not answerable from anything in this repository. If one of these
blocks you, ask:

- **What Core contains**: what every Bridge must run, beneath the profiles an
  adapter requires.
- **The canonical findings model.** One is wanted; the shape is not
  chosen. [`adapter/fixtures/README.md`](adapter/fixtures/README.md)
  states the two published candidates and the constraint keeping the question
  open.
- **Router precedence** when two adapters' detect rules both match a document.
- **The export direction.** Import only is specified; `out/` is not.
- **Cascade's vocabularies.** Their namespaces, the `spec` repository a
  `bridge:vocabularyPin` names, and the stamp predicates a test manifest ignores
  are not in this repository.

Where a document here touches one of these, it says so.

## Start here

The specification exists so two things can be built. Start at the one you are
building; its entry point names what it needs from the other.

| you are building | start at | what it covers |
|---|---|---|
| **an adapter** — a data package for one source format | [`adapter/`](adapter/) | the crate, fixtures, the test manifest, and the seven checks your package must pass |
| **an engine** — a Bridge, the thing that runs adapters | [`engine/`](engine/) | the stages you run around a mapping, and how you execute an adapter's test manifest |

Building either, you also need [`pinning.md`](pinning.md): how you name the
revision of this specification you are built against. To assert that an adapter
and an engine pass together, [`compatibility.md`](compatibility.md).

## Layout

```
adapter/                       building an adapter: its crate, fixtures, test manifest, validation
adapter/profile/               the RO-Crate 1.2 Profile Crate an adapter names in conformsTo
engine/                        building an engine: stages, the sparql-1.1 profile, test manifests
pinning.md                     how adapters and engines name the revisions they were built against
compatibility.md               compatibility.json: the counterparts a repository asserts it passes with
vocab/bridge.ttl               the bridge: vocabulary: adapter, test and compatibility terms
vocab/compatibility.context.jsonld  the JSON-LD context a compatibility.json names
shapes/bridge.shapes.ttl       SHACL shapes for an adapter's crate and its test manifest, as one graph
scripts/validate-adapter.py    the adapter lint: the seven checks of adapter/validation.md
scripts/selftest-lint.py       the mutation cases that show each check failing
scripts/compatibility.py       validate, resolve, check out, run and judge a compatibility.json
scripts/selftest-compatibility.py  its cases, against throwaway repositories
fixtures/synthetic-adapter/    a synthetic adapter package: the lint's own test subject
fixtures/lift/                 the lift vectors a sparql-1.1 Bridge must reproduce
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

That runs the seven checks a conforming adapter package must pass — the crate,
the shapes, the file inventory, the digests, the inputs against their schemas,
the expected graphs and the queries. What each one is, and what a failure
means, is [`adapter/validation.md`](adapter/validation.md); it is the authority
and this is not a second copy of it. Exit status is 0 when the run passes.

**Every check says whether it ran.** `ok`, `nothing to check` and `not run` are
three different sentences: a lint that silently checks nothing is worse than no
lint.

An adapter does not run that by hand. Its CI calls one action from this
repository at a tag that never moves:

```yaml
      - uses: jayostis/cascade-bridge-spec/.github/actions/start@start-v1
```

The starter reads the adapter's `bridge:specPin`, checks this repository out at
exactly that commit, and runs the lint from there, so the pin is written once, in
the crate, and bumping it never touches the workflow. The tools take a
directory and name no adapter — the arrow runs from adapter to specification.
[`compatibility.md`](compatibility.md) has the rest of what the starter runs.

[`adapter/validation.md`](adapter/validation.md) has the full seven-item list a
conforming package must pass, the words a check may be reported in, and the
media types an adapter package may declare.
[`fixtures/README.md`](fixtures/README.md) is the synthetic package the lint is
run against here, and `scripts/selftest-lint.py` is where each check is seen
failing.

## Alignment, in brief

The specification knows about itself. An adapter and a Bridge each know about
the specification, and pin it: the adapter in its crate, the Bridge in its
`compatibility.json`. That pin is the only one required. An adapter and a Bridge
know about each other only by saying so, in an entry of their own
`compatibility.json` that blocks their merge when the pairing fails. **Nothing
here names an adapter or an engine**, and this repository's CI validates this
repository's own files and no one else's. A catalogue is a later publishing
concern, not the place tests run.

A pin is a commit, a tag or a branch, and at merge time it names the
counterpart's default branch or something on it. This specification is upstream
of everything: a change here merges first, and nothing waits on a tag. Commit
and tag pins move in the pull request that needs them, with the measurement
re-run in the same commit; a default-branch pin is the recorded choice to be kept
current. Nothing pins what it does not consume — which is why this repository
pins nothing at all. A comparison is insensitive to everything the format does
not mean. And a Bridge's verdict on an adapter is an EARL report, judged in the
run that produced it and never stored.

The reasoning is in [`pinning.md`](pinning.md).

## Licence

Apache-2.0.
