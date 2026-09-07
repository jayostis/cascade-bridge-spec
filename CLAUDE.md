# cascade-bridge-spec — Agent Context

## Repository purpose

The home of the **Cascade Bridge Specification**: the contract every Cascade
Bridge Adapter and every Cascade Bridge implementation follows. The three proper
nouns are section 2 of the Cascade Bridge RFC,
[the-cascade-protocol/spec#43](https://github.com/the-cascade-protocol/spec/issues/43);
the README repeats them and the layout.

It is DRAFT, thin and pilot-driven. Every artefact here was seeded from phase 1
of the pilot adapter, `cascade-bridge-adapter-clinvar`, and nothing here has yet
been executed by a Bridge, because no Bridge exists. It was created before the
first engine so that the engine is written against a contract with its own home
rather than against files inside one adapter. **No compatibility is promised
before a numbered v1.** Do not re-derive that decision.

## What is normative

These are the specification. A change to any of them is a change to what every
adapter and every Bridge must do, and needs the reasoning recorded in the same
commit:

- `vocab/bridge.ttl` — the `bridge:` vocabulary, namespace
  `https://ns.cascadeprotocol.org/bridge/v1-draft#`. Adapter terms and, on top
  of W3C's `mf:` test-manifest vocabulary, test terms.
- `shapes/bridge.shapes.ttl` — the SHACL shapes an adapter's crate and test
  manifest are validated against as one graph, including the cross-file
  constraints as `sh:sparql`.
- `profile/ro-crate-metadata.json` — the RO-Crate 1.2 Profile Crate an adapter
  names in `conformsTo`. Its IRI is
  `https://ns.cascadeprotocol.org/bridge/v1-draft/adapter-profile/`, and that
  IRI does not dereference yet.
- `docs/adapter-manifest.md`, `docs/test-manifest.md`, `docs/validation.md`,
  `docs/alignment.md` — the prose contract.

`docs/stages.md` and `docs/fixtures-and-provenance.md` are explanatory and name
what is open. `scripts/validate-adapter.py` and
`.github/actions/validate-adapter/action.yml` are machinery, not contract — but
they are the *published* machinery an adapter's CI calls, so a change to either
is a change every adapter feels at its next tag.

**The prose must agree with the Turtle exactly** — term names, cardinalities,
what each shape checks. The Turtle is what runs; a document that disagrees with
it is a second statement of a fact that can disagree, which is the failure mode
this whole project is organised against. When one changes, change both in the
same commit.

## The rules

- **Nothing open on spec#43 is decided here.** What Core contains, the canonical
  findings model, router precedence, the export direction, and where the Bridge
  sits in D-LAYERS-1's layers are the RFC's questions. Where a document touches
  one, it says so and links spec#43. Answering one of them in this repository
  would settle it by accident.
- **No Cascade terms are minted here.** `bridge:` is a Bridge-spec namespace. A
  term in `cascade:`, `genomics:` or any other Cascade vocabulary goes through
  spec's RFC process.
- **This repository must not know that any adapter exists.** The specification
  knows about itself; an adapter and a Bridge know about the specification; a
  catalogue knows about all of them and nothing knows about it. A catalogue of
  adapters, and a CI job that cloned one, were removed at 0.2.0 for pointing
  upward. Prose in `docs/` citing the ClinVar pilot as a worked example is fine;
  a machine-readable reference to a particular adapter — in Turtle, JSON, YAML
  or a workflow — is the bug. Publishing the lint from here is not an
  inversion: the specification publishes an artefact, the adapter consumes it,
  and the lint takes a directory and learns no adapter's name. Neither is
  `fixtures/synthetic-adapter`: it is a package this repository wrote for its
  own lint to run against, entirely invented, with every URL that is not this
  repository's own under `example.org`. It must stay that way. A real adapter
  vendored in as a fixture — as a copy, a submodule or a pinned SHA — is the
  0.2.0 bug wearing a fixture's clothes.
- **A tier is measured, never declared.** RFC section 11. `bridge:tier`,
  `bridge:Universal` and `bridge:Limited` were removed from the vocabulary in
  the move from the pilot and do not come back. A lint may say
  `universal candidate`; a catalogue — a repository of its own, downstream of
  everything, which does not exist yet — records what Bridges actually
  measured, as EARL reports.
- **A comparison is insensitive to everything the format does not mean.** An RDF
  graph does not mean its blank node labels, so they are relabelled; a findings
  array does not mean its element order, so it is compared as a multiset. A
  stricter rule than the format's meaning does not catch more mapping errors, it
  only fails harnesses that are right.
- **Standards, not inventions.** RO-Crate 1.2 for the package, W3C's `mf:` for
  the test manifest, SHACL for the shapes, Enterprise Integration Patterns for
  the stage names, EARL for results, SKOS for a concept table. If something here
  seems to need a new convention, first find the published one.
- **The pilot is evidence, not authority.** A fact taken from
  `cascade-bridge-adapter-clinvar` is written down here as a fact about *an*
  adapter, generalised, with ClinVar as the example. Do not modify that
  repository from here.

## Pinning

Adapters and Bridges pin this repository by commit, and **every commit anything
pins must be tagged here**, verified with `git ls-remote` before the pin lands.
A branch tip is not a guarantee: a pin to an untagged commit dies at
`git checkout` the first time a branch is reset or rebased, and it takes CI on
unrelated pull requests down with it. That reasoning is
`conformance/scripts/SPEC_PIN`'s, and `docs/alignment.md` carries it in full
along with the rest: dependencies point one way (spec ← adapter ← Bridge), pins
move in the pull request that needs them, nothing pins what it does not consume,
and a Bridge's verdict on an adapter flows to a catalogue as a report rather
than as a pin.

This repository pins nothing, in either direction. An adapter's pin is checked
where the adapter lives: its CI calls
`jayostis/cascade-bridge-spec/.github/actions/validate-adapter@<tag>`, and the
action compares the SHA behind that tag against the `bridge:specPin` in the
adapter's crate. The `uses:` ref and the crate's pin are the same fact written
twice and move together.

## Sibling checkouts this repository cites

Expected beside this repository, as sister directories:

- `../bridge-adapter-clinvar` — the pilot adapter
  (`jayostis/cascade-bridge-adapter-clinvar`). `vocab/bridge.ttl` and
  `shapes/bridge.shapes.ttl` here were seeded from its `schema/manifest/` at
  `0b2d548`, and each file's header lists exactly what changed in the move; the
  `sh:class schema:MediaObject` constraints and the multiset findings rule were
  improved there during its own review and carried up here at 0.2.0. It is a
  checkout to test the lint against, by hand, when a shape changes. It is not
  named anywhere a machine reads, and adding it back to one is the bug this
  repository was corrected for at 0.2.0.
- `../spec` — the Cascade vocabularies and the RFC (spec#43; identity is
  spec#38). Nothing here pins it: this specification writes no Cascade term, so
  it consumes no vocabulary revision. An adapter pins it, with
  `bridge:vocabularyPin`.
- `../conformance` — `scripts/SPEC_PIN` is where the pinning discipline in
  `docs/alignment.md` comes from, quoted rather than paraphrased.
- `../cascade-cli` — the runtime whose converters an adapter re-expresses as
  data, and whose `tests/clinvar-conformance.test.ts` is the comparison
  `bridge:IsomorphicConversionTest` restates.

## What to run

There is no test suite. These are the checks, and a commit says which ran:

```bash
python3 -m pip install pyshacl rdflib roc-validator lxml

# every Turtle file parses
python3 -c "from rdflib import Graph; [Graph().parse(f) for f in ['vocab/bridge.ttl','shapes/bridge.shapes.ttl']]"

# the shapes are valid SHACL
python3 -m pyshacl --metashacl --shacl shapes/bridge.shapes.ttl shapes/bridge.shapes.ttl

# the profile crate is a valid RO-Crate 1.2
rocrate-validator validate profile/ --profile-identifier ro-crate-1.2

# the lint passes the synthetic package this repository owns
python3 scripts/validate-adapter.py fixtures/synthetic-adapter

# and can be seen failing: one broken property per case, on a temporary copy
python3 scripts/selftest-lint.py

# the published lint still accepts a real adapter package
python3 scripts/validate-adapter.py <path to an adapter checkout>
```

The first five run in `.github/workflows/validate.yml`, in two jobs: this
repository's own files, and the published lint against `fixtures/`, which is a
synthetic package this repository wrote and owns. A fixture, never a real
adapter — `fixtures/README.md` says why that distinction is the whole point.

**The last is run by hand and is not in CI, on purpose.** CI here validates
this repository's own files and no one else's: a job that cloned an adapter
would make this repository red because of a property missing from somebody
else's, and would grow a job per adapter for as long as adapters keep being
written (`docs/alignment.md`). But changing a shape without running the lint
against a real adapter checkout is how this repository breaks a real adapter
without noticing, so run it, against a sibling checkout, and say in the commit
which adapter and at which commit. Verify a shape that is meant to reject
something by mutation — red first, then green — without adding that adapter to
this repository in any form.

CI here is Linux and invokes `python3` directly. Do not commit any
machine-specific way of running it.

## Conventions

- Conventional commits: `feat(spec): ...`, `docs: ...`, `fix(shapes): ...`.
- Issue and document text is written impersonally, as findings and decisions,
  not as promises by a person.
- `CHANGELOG.md` is updated in the same commit as the change it describes; its
  format is Keep a Changelog and its versions are semantic.
- Every fact taken from the RFC or from a sibling repository names its source.
