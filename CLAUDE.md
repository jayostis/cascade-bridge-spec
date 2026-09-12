# cascade-bridge-spec — Agent Context

The home of the **Cascade Bridge Specification**: the contract every Cascade
Bridge Adapter and every Bridge implementation follows.

DRAFT, thin and pilot-driven. Every artefact was seeded from phase 1 of the pilot
adapter, and nothing has yet been executed by a Bridge, because no Bridge exists.
**No compatibility is promised before a numbered v1.** Do not re-derive that.

## What is normative

`vocab/bridge.ttl`, `shapes/bridge.shapes.ttl`, `profile/ro-crate-metadata.json`,
and in `docs/`: `adapter/manifest.md`, `adapter/test-manifest.md`,
`adapter/validation.md`, `pinning.md`. Changing any of them changes what every
adapter and every Bridge must do, and needs its reasoning recorded in the same
commit. The rest is explanatory, machinery, or the lint's own test subject:
see each directory.

**The prose must agree with the Turtle exactly** — term names, cardinalities,
what each shape checks. The Turtle is what runs, and a document disagreeing with
it is the failure mode this project is organised against. Change both in one
commit.

## The rules

- **What is unsettled stays unsettled here.** What Core contains, the canonical
  findings model, router precedence and the export direction are open. A document
  touching one says so; answering one here would settle it by accident.
- **No Cascade terms are minted here.** `bridge:` only; a term in `cascade:` or
  `genomics:` goes through spec's own process.
- **This repository must not know that any adapter exists.** The specification
  knows about itself; an adapter and a Bridge know about the specification; a
  catalogue knows about all of them and nothing knows about it. Prose citing the
  ClinVar pilot as an example is fine; a machine-readable reference to a
  particular adapter is the bug. Publishing the lint is not an inversion: it
  takes a directory and learns no adapter's name.
- **A tier is measured, never declared.** A lint may say
  `universal candidate`; a catalogue records what Bridges measured, as EARL.
- **Standards, not inventions.** RO-Crate 1.2, W3C's `mf:`, SHACL, Enterprise
  Integration Patterns for stage names, EARL for results, SKOS for a concept
  table. If something seems to need a new convention, find the published one.
- **The pilot is evidence, not authority.** A fact taken from the pilot adapter
  is written here generalised. Do not modify it here.
- **Everything that pins this repository pins a tag**, verified with
  `git ls-remote` first: a pin to an untagged commit dies at `git checkout` the
  first time a branch is reset. This repository pins nothing, in either
  direction; `docs/pinning.md` is the mechanism in full.

## Where a rule goes

This file holds what has to be known *before* choosing a directory to open.
Everything else belongs in a `CLAUDE.md` in the directory it governs, which loads
only when that directory is touched. Keep this file under 80 lines.

## Conventions

- Conventional commits: `feat(spec): ...`, `docs: ...`, `fix(shapes): ...`.
- Impersonal: findings and decisions, not promises by a person.
- **Say it once.** A fact in the vocabulary or the shapes is linked,
  never restated: two statements of one contract can disagree, and have.
- **No archaeology.** What a file used to be, and what changed in a move, is
  git's job. Not a header, not a comment.
- **Why, never what.** A comment restating the line below it goes. A reason that
  belongs to a term goes in its `rdfs:comment` or `sh:description`, where it is
  machine-readable, not in a header block above it.
