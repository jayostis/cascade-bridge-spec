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
| **an adapter** — a data package for one source format | [`adapter/`](adapter/) | the crate, fixtures, the test manifest, and the checks your package must pass |
| **an engine** — a Bridge, the thing that runs adapters | [`engine/`](engine/) | the stages you run around a mapping, and how you execute an adapter's test manifest |

Building either, you also need [`pinning.md`](pinning.md): how you name the
revision of this specification you are built against, and why the specification
names no adapter and no engine. To assert that a particular adapter and a
particular engine pass together, [`compatibility.md`](compatibility.md).

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
scripts/validate-adapter.py    the adapter lint: the checks of adapter/validation.md
scripts/selftest-lint.py       the mutation cases that show each check failing
scripts/compatibility.py       validate, resolve, check out, run and judge a compatibility.json
scripts/selftest-compatibility.py  its cases, against throwaway repositories
fixtures/synthetic-adapter/    a synthetic adapter package: the lint's own test subject
fixtures/lift/                 the lift and envelope-skeleton vectors a sparql-1.1 Bridge must reproduce
.github/actions/start/         the starter, which every adapter's and engine's CI calls at start-v1
.github/actions/validate-adapter/  the lint published as an action, which the starter calls
.github/actions/compatibility/ compatibility.json's entries, checked out, run and judged
.github/actions/ready-to-merge/  the merge gate, meant to be a required status check
.github/workflows/validate.yml CI: this repository's own files, and nothing else's
```

## Licence

Apache-2.0.
