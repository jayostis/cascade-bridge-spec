# cascade-bridge-spec — Agent Context

The home of the **Cascade Bridge Specification**: the contract every Cascade
Bridge Adapter and every Bridge implementation follows.

DRAFT, thin and pilot-driven. Every artefact was seeded from phase 1 of the pilot
adapter.
**No compatibility is promised before a numbered v1.** Do not re-derive that.

## What is normative

`vocab/bridge.ttl`, `vocab/compatibility.context.jsonld`,
`shapes/bridge.shapes.ttl`, `pinning.md`, `compatibility.md`, `engine/sparql.md`,
`engine/command.md`, and in `adapter/`: `profile/ro-crate-metadata.json`,
`ro-crate-metadata.md`, `fixtures/manifest.md`, `validation.md`. Changing any of
them changes what every adapter and every Bridge must do, and needs its reasoning
recorded in the same commit. The rest is explanatory, machinery, or the lint's
own test subject: see each directory.

**The prose does not restate the Turtle, it links it.** A term's cardinality and
meaning are its `rdfs:comment`; what is checked is the shape's `sh:message`. A
document names the term and gives the reasoning neither has room for. Prose that
agrees with the Turtle today can disagree with it tomorrow, and the only fix
that holds is not having the second copy.

## The rules

- **What is unsettled stays unsettled here.** Core, the canonical findings
  model, router precedence and the export direction are open. A document
  touching one says so; answering one here would settle it by accident.
- **v1-draft is XML sources and the `sparql-1.1` profile.** Another source format
  or mapping language arrives as its own specified addition, not a mention.
- **No Cascade terms are minted here.** `bridge:` only; a term in `cascade:` or
  `genomics:` goes through spec's own process.
- **This repository must not know that any adapter or engine exists.** It knows
  about itself; an adapter and a Bridge know about it, and about each other only
  through a `compatibility.json` of their own. Prose citing the ClinVar pilot as
  an example is fine; a machine-readable reference to one is the bug. Publishing
  the tooling is not an inversion: it takes a directory and learns no one's name.
- **Tiers are not specified in v1-draft.** When they are, they are measured,
  never declared: an adapter declares no tier.
- **Standards, not inventions.** RO-Crate 1.2 and its profile mechanism, W3C's
  `mf:`, SHACL, Enterprise Integration Patterns for stage names, EARL for
  results, SKOS for a concept table. If something seems to need a new
  convention, find the published one — and prefer its vocabulary to one of ours.
- **The pilot is evidence, not authority.** A fact from it is written here
  generalised, and it is never modified here.
- **Everything that pins this repository names, at merge time, a commit or tag
  on its default branch, or that branch**: a pin to a feature branch's commit
  dies at `git checkout` the first time the branch is reset. A downstream pull
  request may pin a branch here while both are open. This repository pins
  nothing; `pinning.md` is the mechanism and `compatibility.md` the file.

## Where a rule goes

This file holds what has to be known *before* choosing a directory to open.
Everything else belongs in a `CLAUDE.md` in the directory it governs, which loads
only when that directory is touched. Keep this file under 80 lines.

A `README.md` addresses whoever is building something that must conform; a
`CLAUDE.md` addresses whoever is changing this repository, so rules for authoring
an adapter never go in one. Conformance targets are top-level (`adapter/`,
`engine/`), each holding its own contract; `vocab/` and `shapes/` are the spine
they share; `scripts/` and `fixtures/` are machinery, never inside a target.
`.github/` is where GitHub requires it.

## Conventions

- Conventional commits: `feat(spec): ...`, `docs: ...`, `fix(shapes): ...`.
- Impersonal: findings and decisions, not promises by a person.
- **Say it once**, between documents as much as against the Turtle: two
  statements of one contract can disagree, and have. A **test** may restate it —
  prose disagrees in silence, a test fails the build — so its name is the
  sentence it asserts, and the assertion is the documentation.
- **No archaeology.** What a file used to be, and what changed in a move, is
  git's job. Not a header, not a comment.
- **Why, never what.** A comment restating the line below it goes. A reason that
  belongs to a term goes in its `rdfs:comment` or `sh:description`, where it is
  machine-readable, not in a header block above it.
