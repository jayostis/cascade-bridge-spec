# Changelog

All notable changes to the Cascade Bridge Specification are recorded here. The
format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow semantic versioning.

The specification is DRAFT and no compatibility is promised before a numbered
v1. Every namespace is `v1-draft`; terms may be renamed and cardinalities may
change between 0.x releases.

## [0.1.0] - 2026-09-06

The specification seeded from phase 1 of the pilot adapter,
[cascade-bridge-adapter-clinvar](https://github.com/jayostis/cascade-bridge-adapter-clinvar),
at `beeae97`. Everything in this release was proven against exactly one adapter
and executed by no Bridge, because none exists. It is published now so that the
phase 2 engine is written against a contract with its own home rather than
against files inside one adapter.

### Added

- `vocab/bridge.ttl`, the `bridge:` vocabulary
  (`https://ns.cascadeprotocol.org/bridge/v1-draft#`), with an `rdfs:comment` on
  every term: the adapter terms an adapter's RO-Crate root entity and envelopes
  use, and, on top of W3C's `mf:` test-manifest vocabulary, the three test types
  that carry the comparison rule and the properties a test manifest uses. Moved
  from the pilot's `schema/manifest/bridge.ttl` at `0b2d548` with three changes,
  listed in the file's own header: `bridge:Tier`, `bridge:Universal`,
  `bridge:Limited` and `bridge:tier` removed, because RFC section 11 measures a
  tier and an adapter declares none; `bridge:specPin` added, the commit of this
  specification an adapter is written against, the same shape as
  `bridge:vocabularyPin`; and `bridge:profileRequired` loses its `rdfs:domain`
  so a catalogue entry can restate an adapter's profiles without being typed an
  adapter.
- `shapes/bridge.shapes.ttl`, the SHACL shapes an adapter's crate and its test
  manifest are validated against as one graph, each parsed with its own file
  location as base. Cross-file constraints are `sh:sparql`: the adapter and the
  manifest point at each other, and every envelope a test names is one the
  adapter lists. Moved from the pilot's `schema/manifest/bridge.shapes.ttl` at
  `0b2d548`, with the `bridge:tier` property shape removed, a `bridge:specPin`
  property shape added (exactly one, by IRI), and a warning when the crate root
  does not name the adapter profile in `conformsTo`.
- `profile/ro-crate-metadata.json`, an RO-Crate 1.2 Profile Crate for a Cascade
  Bridge Adapter, whose IRI is
  `https://ns.cascadeprotocol.org/bridge/v1-draft/adapter-profile/` and whose
  constraints resource is the SHACL shapes. That IRI does not dereference; until
  it does, the specification is read from this repository. Two shapes in the file
  are the RO-Crate validator's requirements rather than the specification's and
  are recorded in the file's own description: the shapes and vocabulary are named
  as web-based data entities because a data entity's `@id` must resolve inside the
  crate root, and the profile IRI is carried as `identifier` because a crate's
  root entity `@id` is the crate directory.
- `docs/adapter-manifest.md`, the adapter manifest contract: the crate at the
  package root, the root entity's seventeen properties with their cardinalities,
  the two properties that together declare conformance, envelope entities, the
  detect XPath, and the three things phase 2 adds (`mainEntity` under Workflow
  RO-Crate, tables as SKOS, an extension vocabulary).
- `docs/test-manifest.md`, the test manifest contract: why the `mf:` shape, the
  manifest's own properties, the three test types and what each judges, the
  isomorphism comparison rule, ignore predicates stated once on the manifest and
  inherited by every entry, and why a dataset test needs a fetchable dataset.
- `docs/fixtures-and-provenance.md`: committed inputs and their digests,
  referenced datasets, the input / expected / findings triplet and why names are
  kept from their source even when wrong, and the findings sidecar as it stands
  with its open question named — Web Annotation with XPath selectors for
  source-side findings, SHACL results for graph-side, to be settled on spec#43
  section 8 before a second adapter writes findings.
- `docs/stages.md`, the RFC's engine stages named with their Enterprise
  Integration Patterns equivalents, generalised from the pilot: the third column
  is what an adapter contributes to each stage, with ClinVar as the example
  rather than the subject.
- `docs/validation.md`, the six checks a conforming adapter package must pass,
  written as the list a lint implements; which two run today; and what the lint
  computes and in what words — `universal candidate` when the inventory holds no
  code and every required profile is in Core, otherwise
  `limited: requires <profiles>`. The lint will be a reusable GitHub Action
  published from this repository and is not built.
- `docs/alignment.md`, the rules that keep spec, adapters and Bridges in step:
  dependencies point one way, every dependency is a SHA, every pinned SHA is
  tagged, pins move in the pull request that needs them, nothing pins what it
  does not consume, this repository's CI validates every catalogued adapter at
  its pin, and a Bridge's results reach the catalogue as EARL reports rather than
  as a pin. The reasoning against syncing to `main` is quoted from
  `conformance/scripts/SPEC_PIN`.
- `catalog/adapters.ttl`, the catalogue of known adapters: one entry, the ClinVar
  pilot at `beeae97b841f1e0384cb7ba4e3d5d998249bfacf`, with its repository, its
  licence and the one profile it requires, `xslt-3`. No tier, and no term minted
  for the catalogue: an entry is a `schema:SoftwareSourceCode` with
  `codeRepository` and `version`, and `bridge:profileRequired` restates the
  adapter's own.
- `scripts/validate-adapter.py`, which runs the RO-Crate 1.2 validation and the
  SHACL conformance for one adapter checkout, setting both base IRIs explicitly
  because loading either file with the wrong base turns every link between them
  into two unrelated nodes and makes the shapes report nothing. It names a
  missing `bridge:specPin` in its own words, which is the one failure every
  adapter written before this repository existed will hit.
- `.github/workflows/validate.yml`: Turtle parses, SHACL meta-validation of the
  shapes, RO-Crate validation of the profile crate, and then each catalogued
  adapter cloned at its pinned commit and validated.
- `LICENSE` (Apache-2.0), `README.md`, `CLAUDE.md`, `.gitattributes` and
  `.editorconfig` (LF everywhere, final newline).

### Known state

- No Bridge exists, so no test manifest has been executed, no EARL report exists
  and no adapter has a measured tier.
- The pilot adapter at the catalogued commit carries no `bridge:specPin` and does
  not name the profile IRI in `conformsTo`; it was written before this repository
  did. `scripts/validate-adapter.py` reports the first as a failure and the second
  as a warning, which is the intended result until the adapter's next pull request
  adds both. CI's adapters job is therefore red at this release, on exactly that
  one failure. It goes green when the adapter adds the pin and a pull request here
  moves the catalogue's SHA to it, and not by weakening the check.

[0.1.0]: https://github.com/jayostis/cascade-bridge-spec/releases/tag/v0.1.0
