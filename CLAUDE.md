# cascade-bridge-spec — Agent Context

The Cascade Bridge Specification: the contract every Cascade Bridge Adapter and
every Bridge follows. DRAFT; no compatibility is promised before a numbered v1.

## Documentation is a defect until proven otherwise

Anything that restates something else goes stale, so the default is to write
nothing. What something is and what it must do is carried, in this order, by:

1. **A name** that makes a comment unnecessary: a term, a field, a function, a file.
2. **Structure**: the crate, the directory layout, a shape's constraints.
3. **A test** whose name is the sentence and whose assertion is the specification.
4. **A shape's `sh:message`**, because a failing run prints it.
5. **Prose**, only for what none of the above can hold, and as short as it goes.

So:

- **No comment, docstring, `rdfs:comment` or `sh:description` that restates a
  name, a signature, a constraint or another file.** Rename instead. A term
  whose name says what it is needs no `rdfs:comment`; cardinality is the shape's.
- **No reference by number, count, position or line**: "check 5", "the three
  types", "below", `file.py:120`. Name the thing, or link it.
- **No reasoning in files.** Why a change was made goes in the commit message.
- **Deleting prose is always in scope**, in any change, and preferred to editing it.
- **A behaviour this repository cannot run** (a Bridge's) is specified by vectors
  under `fixtures/` first, and by the shortest normative sentence only where a
  vector cannot say it.

## The guidelines

Each holds until the design it describes changes, and then it changes with it.

- **Standards, not inventions**: RO-Crate 1.2 and its profiles, W3C `mf:`,
  SHACL, EARL, SKOS, Enterprise Integration Patterns.
- **Which versions run together is OpenStack's Zuul model**
  ([gating](https://zuul-ci.org/docs/zuul/latest/gating.html),
  [job configuration](https://zuul-ci.org/docs/zuul/latest/config/job.html),
  [queues](https://zuul-ci.org/docs/zuul/latest/config/queue.html)), followed as
  closely as practical. A departure from it, forced or chosen, is named in
  [`compatibility.md`](compatibility.md) with what someone must do by hand
  instead, or it is not taken.
- **A breaking change is handled by that model, not by a transitional path.**
  Before a numbered v1, nothing here grows a second accepted form to keep a
  default branch green: the work branches share one name, so each repository's
  CI runs against the others' while all are open, and they merge in sequence.
  A default branch is red between the first merge and the last.

## Layout

Conformance targets are top-level (`adapter/`, `engine/`), each holding its
contract and the profile that checks it; `vocab/` and `shapes/` are shared;
`scripts/`, `fixtures/` and `tests/` are machinery. A `CLAUDE.md` holds a rule
for changing the directory it sits in, and only that.

## Conventions

- Conventional commits: `feat(spec): ...`, `docs: ...`, `fix(shapes): ...`.
- A change to `vocab/`, `shapes/`, `adapter/profile/`, `engine/sparql.md`,
  `engine/command.md`, `pinning.md` or `compatibility.md` changes what every
  adapter and Bridge must do; its commit message says why.
