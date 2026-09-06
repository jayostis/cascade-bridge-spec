# Changelog

All notable changes to the Cascade Bridge Specification are recorded here. The
format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow semantic versioning.

The specification is DRAFT and no compatibility is promised before a numbered
v1. Every namespace is `v1-draft`; terms may be renamed and cardinalities may
change between 0.x releases.

## [0.2.0] - 2026-09-06

The specification stops knowing which adapters exist, and starts publishing the
lint an adapter's own CI calls. At 0.1.0 this repository carried a catalogue
naming one adapter, its repository and a commit of it, and a CI job that cloned
that repository at that commit; both point upward, and `docs/alignment.md` says
in the same breath that dependencies point one way. The consequence was not
theoretical: this repository's CI was red on a property missing from somebody
else's repository, and with fifty adapters it would clone fifty repositories on
every push.

### Removed

- `catalog/adapters.ttl` and the `catalog/` directory. A catalogue of adapters
  and engines is still wanted — RFC section 9 asks for one — but it is a
  repository of its own, downstream of every adapter and every Bridge, warranted
  when more than one adapter exists and at least one Bridge is producing
  results. Nothing about it belongs here. Tracked as issue #6.
- The `adapters` job in `.github/workflows/validate.yml`, which read that
  catalogue, cloned each named repository at its pinned commit and validated it.
  The `spec` job is now the whole of this repository's CI, and it is green.
- Every machine-readable reference to a particular adapter. What remains is
  prose: `docs/` cites the ClinVar pilot as the worked example it is, and the
  vocabulary and shapes record in their file headers which adapter they were
  seeded from, which is a fact about their history rather than a dependency.

### Added

- `.github/actions/validate-adapter/action.yml`, the lint published as a
  composite GitHub Action, so an adapter repository's CI is one `uses:` line
  pinned at a tag of this repository rather than the checks copied between
  adapters. It takes a path (default: the repository root), names no adapter and
  no format, and clones nothing but the caller's own checkout. Publishing it
  from here is not an inversion: the specification publishes an artefact and the
  adapter consumes it, so the arrow runs from adapter to specification. Part of
  issue #1, which stays open for checks 4 to 6.
- Check 3 of `docs/validation.md`, the file inventory, in
  `scripts/validate-adapter.py`: every git-tracked file is either a crate entity
  carrying a declared `encodingFormat` or is in the allowlist. Taken with
  `git ls-files`, because a directory walk counts build output nobody can keep
  green. This is the check that makes "an adapter is data" measured rather than
  claimed.
- `<#DescribedFile>` in `shapes/bridge.shapes.ttl`: every declared
  `encodingFormat` is one of twelve media types, listed in the shapes and
  restated in `docs/validation.md`. The set is where "no code" is enforced — not
  by scanning a file for a language, but by refusing one whose media type says
  it executes.
- The specification pin is checked rather than only declared. The action
  resolves the ref it was called at to a SHA and passes it to the lint as
  `--spec-revision`; a crate whose `bridge:specPin` names a different commit
  fails. The `uses:` ref and the crate's pin are the same fact written twice,
  and they move together. Where the ref cannot be resolved, the run says so
  rather than quietly checking nothing.
- The lint reports the tier line `docs/validation.md` specifies —
  `universal candidate` or `limited: requires <profiles>` — and names checks 4
  to 6 as not run, so a package is never reported as passing a check that did
  not happen.

### Changed

- `shapes/bridge.shapes.ttl`: the five file-valued property shapes —
  `bridge:input`, `bridge:graph`, `bridge:findings`, `bridge:sourceSchema`,
  `bridge:documentSchema` — carry `sh:class schema:MediaObject`, what the
  RO-Crate 1.2 context expands `File` to. `sh:nodeKind sh:IRI` alone let a typo
  through, because an IRI naming no entity at all is still an IRI. Improved in
  the pilot adapter during its own review and carried up here, because the
  adapter's copy of the shapes is being deleted and the improvement would
  otherwise be lost. Verified by mutation against a real adapter checkout: each
  of the five pointed at a name no crate entity carries conformed before and
  fails now.
- `vocab/bridge.ttl`: `bridge:IsomorphicConversionTest` and `bridge:findings`
  compare the produced findings against the expected sidecar as a **multiset** —
  the same entries with the same multiplicity, in any order, JSON object
  equality — where they required them equal entry for entry in a sort order.
  Also improved in the pilot and carried up. The ordering requirement appeared
  in no standard and no upstream: `cascade-cli`'s own test sorts only the actual
  side. It made a correct mapping fail on any harness whose string comparison is
  not JavaScript's, because the oracles were written with `localeCompare`, which
  is ICU collation, in which `/` precedes `@` although U+002F is above U+0040;
  78, 56, 6 and 1 adjacent pairs across the four committed sidecars are out of
  code-point order. Multiplicity is compared, because entries repeat and the
  repeats are identical. Sorting a sidecar by Unicode code point is file
  hygiene, a SHOULD on the file, and never part of the comparison. The general
  principle now stated in `docs/alignment.md` and `docs/test-manifest.md`: **a
  comparison is insensitive to anything the format does not mean.**
- `vocab/bridge.ttl`: `bridge:profileRequired` has its `rdfs:domain
  bridge:Adapter` back. It was dropped at 0.1.0 so that a catalogue entry — a
  `schema:SoftwareSourceCode` standing for an adapter at a commit — could
  restate an adapter's profiles without being typed an adapter. With the
  catalogue gone that reason lapses, and the domain is the honest statement
  again: only an adapter requires a profile. A future catalogue in its own
  repository will hold EARL reports and queries over them, not a restatement of
  an adapter's own manifest, so it does not need the domain dropped again.
- `docs/alignment.md` is rewritten around what knows about what, with the
  removal, the action, the pin-agreement rule and the insensitive-comparison
  principle stated. The pinning discipline quoted from
  `conformance/scripts/SPEC_PIN` is unchanged and carried over in full.
- `docs/validation.md` names the allowed media types, describes the action as
  published rather than as not built, and says which checks are still specified
  and not built.
- `docs/test-manifest.md`, `docs/fixtures-and-provenance.md`,
  `docs/adapter-manifest.md`, `README.md` and `CLAUDE.md` follow the two changes
  above and stop describing a catalogue in this repository.

### Known state

- No Bridge exists, so no test manifest has been executed, no EARL report exists
  and no adapter has a measured tier.
- Checks 4 to 6 of `docs/validation.md` — the digests, the source-schema
  validation, the expected graphs — are specified and not built. Issue #1 stays
  open for them.
- `.github/workflows/validate.yml` runs one job. It validates this repository's
  own files and exercises the published lint against a package built to fail; it
  validates no adapter, by design.

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

[0.2.0]: https://github.com/jayostis/cascade-bridge-spec/releases/tag/v0.2.0
[0.1.0]: https://github.com/jayostis/cascade-bridge-spec/releases/tag/v0.1.0
