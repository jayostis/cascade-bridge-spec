# Keeping the specification, the adapters and the Bridges aligned

Several repositories' worth of artefacts have to agree about which revision of
which vocabulary and which contract they were built against. The pins have to be
visible and testable in CI. This document is the mechanism.

## What knows about what

- **The specification knows about itself.** It defines the contract and
  publishes the tooling that enforces it. It names no adapter and no engine.
- **An adapter knows about the specification.** It pins a revision of it, in its
  crate as `bridge:specPin`.
- **A Bridge knows about the specification.** It pins a revision of it too, in
  its `compatibility.json`, because it has no crate. It reads adapters at run
  time, which is being handed an input, not depending on a particular one.
- **An engine and an adapter may know about each other, and only by saying so.**
  A relationship between them is optional and declared, never implied: an entry
  in one side's `compatibility.json`, which is an assertion that the pairing
  passes ([`compatibility.md`](compatibility.md)).

The spec pin is the only pin every repository must carry. A pin from a Bridge to
an adapter, or from an adapter to a Bridge, is opt-in, and the repository that
opts in is the one whose merge it blocks.

A catalogue of adapters and Bridges is a later publishing concern, not the place
tests run.

### The specification does not know which adapters or engines exist

A check belongs with the thing it checks. A specification that named adapters,
or cloned one in CI, would go red for a property missing from somebody else's
repository, would clone every adapter on every push, and would put diagnosis on
whoever did not cause the failure. An adapter or an engine can live on any
account in any organisation, and this specification must stay checkable without
knowing that one exists. Every check therefore runs in the adapter or the engine,
against the head being proposed.

## Every repository's CI calls the starter

The tooling is published from here as composite GitHub Actions. A repository's
CI calls one of them, `start`, at the reserved tag `start-v1`, which never moves.
The starter reads the repository's own spec pin, checks this repository out at
exactly that commit, and runs the real tools from there. Bumping the spec pin
therefore never touches the workflow, and the pin is written in one place: the
crate for an adapter, `compatibility.json` for an engine.
[`compatibility.md`](compatibility.md) has the line.

**Publishing the tooling from here is not an inversion.** The specification
publishes an artefact and the adapter or engine consumes it, so the arrow runs
towards the specification, the way it must. The tools take a directory and read
the files in it. They never learn that any particular adapter or engine exists,
and they name none.

## A pin is a commit, a tag or a branch

In a crate, `bridge:specPin` is a full 40-character commit SHA. In a
`compatibility.json`, a pin names a commit, a tag or a branch, and every run
records the commit each resolved to; [`compatibility.md`](compatibility.md) says
how each kind resolves and what each guarantees.

**At merge time, every pin names the counterpart's default branch or something
on it**: a commit or a tag on that branch, or the branch itself. A pin to any
other branch is refused by the `ready-to-merge` check. That is what keeps a pin
reachable: a commit on the default branch survives a feature branch being reset
or rebased, where a commit only on that feature branch would leave every later
CI run dying at `git checkout` on an object that has been garbage-collected.

A pin is written as an entity, not a string: a repository and a revision. The
repository half is carried explicitly because a commit that exists only on a
fork must name the fork, or CI clones a repository that does not hold the
object. This specification's repository is
`https://github.com/jayostis/cascade-bridge-spec`; there is no other copy to pin.

## Changes flow downstream

This specification is upstream of every engine and every adapter. A change here
merges first; a downstream pull request that needs it pins this repository's
feature branch while both are open, and swaps that for the merge commit once
this side has merged. Nothing waits on a tag: a tag is a label on a commit that
has already passed, not a step between a merge and the pin that uses it.

The same direction holds between an engine and an adapter that name each other.
The side that changes first merges first, and the other follows against its
merged commit.

## Pins move in the pull request that needs them

A commit or tag pin is not swept forward on a schedule. It moves when a change
needs what the new revision contains, in the pull request that makes the change,
and that pull request re-measures whatever the pin's numbers are and records the
before and after.

Why not track a moving target silently: a suite pinned to one passes today for a
different reason than it passed yesterday, and the difference is invisible.
Worse, the failure surfaces in whichever unrelated pull request happens to run
next, so the person who has to diagnose it is never the person who caused it.
The other extreme costs as much: measured counts that have gone stale against
the pin. A mandatory-verification section quoting numbers no run can reproduce
teaches the reader to disbelieve the section. Both failures are avoided by the
same rule: the pin and the measurement move together, in one deliberate commit.

A default-branch pin in a `compatibility.json` is the one pin that moves without
a commit here, and it is a choice the file records rather than an accident: the
repository has asked to be kept current and blocked when the other side breaks
it.

## Nothing pins what it does not consume

A pin is a statement that this artefact reads that revision. An adapter pins one
revision of the Cascade vocabularies (`bridge:vocabularyPin`) because it always
writes at least one of them, and names only those it writes
(`bridge:vocabulary`): one that writes no `genomics:` term does not name the
genomics vocabulary. A Bridge that implements no profile an adapter requires
does not list that adapter. Pins added
"for completeness" are pins nobody re-measures, and an unre-measured pin is a
stale fact with a SHA attached to make it look checked.

It is why this repository pins nothing at all. It writes no Cascade term, so it
consumes no vocabulary revision; it runs no adapter and no engine, so it
consumes no one's commit.

## A comparison is insensitive to everything the format does not mean

Not a pinning rule, but the same failure wearing different clothes: a contract
that asserts more than it means makes correct work fail, and the failure lands on
whoever runs it next rather than on whoever wrote it.

An RDF graph does not mean its blank node labels, and a findings array does not
mean its element order, so [`adapter/fixtures/manifest.md`](adapter/fixtures/manifest.md)
compares graphs up to relabelling and findings as a multiset. A stricter rule
than the format's meaning does not catch more mapping errors; it only fails
harnesses that are right.

## Results are reports, not stored facts

A Bridge's verdict on an adapter is an EARL report
([`engine/executing.md`](engine/executing.md)). The tooling judges it in the run
that produced it, and it is kept as that run's artifact. It is never written
back into the adapter, the Bridge or this repository: a stored result is a
measurement that goes stale against the pins that produced it.
