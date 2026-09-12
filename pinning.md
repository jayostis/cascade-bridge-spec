# Keeping the specification, the adapters and the Bridges aligned

Several repositories' worth of artefacts have to agree about which revision of
which vocabulary and which contract they were built against. The pins have to be
visible and testable in CI. This document is the mechanism.

## What knows about what

- **The specification knows about itself.** It defines the contract and
  publishes the lint that enforces it. It names no adapter and no engine.
- **An adapter knows about the specification.** It pins a revision of it, in its
  crate as `bridge:specPin` and in its CI as the ref it calls the lint at.
- **A Bridge knows about the specification.** The same way. It reads adapters at
  run time, which is being handed an input, not depending on a particular one.
- **A catalogue knows about all of them, and nothing knows about the
  catalogue.** It is downstream of everything.

The direction is the whole discipline. An adapter that pinned a Bridge would be
an adapter that runs on one Bridge, which is the opposite of what "an adapter is
data" is for; a specification that pinned an implementation would be a
specification the implementation could change.

The cost is real and accepted: more repositories to keep in step.

### The specification does not know which adapters exist

A check belongs with the thing it checks. A specification that named adapters,
or cloned one in CI, would go red for a property missing from somebody else's
repository, would clone every adapter on every push, and would put diagnosis on
whoever did not cause the failure. An adapter can live on any account in any
organisation, and this specification must stay checkable without knowing that
one exists. The check therefore runs in the adapter, against the head being
proposed — the next section.

A catalogue is downstream of every adapter and every Bridge. It does not exist,
and nothing about it belongs here.

## An adapter's CI calls this repository's lint

The lint is published from here as a composite GitHub Action, so an adapter's
whole CI is two lines: [`validation.md`](adapter/validation.md) has them.

**Publishing the lint from here is not an inversion.** The specification
publishes an artefact and the adapter consumes it, so the arrow runs from adapter
to specification, the way it must. The action takes a directory and validates it
against these shapes. It never learns that any particular adapter exists, it
names none, and it clones nothing but the caller's own checkout.

**The tag in that `uses:` line is the adapter's `bridge:specPin` in executable
form.** The two name the same commit of this repository, one for the machine and
one for the reader, and they move together in the same pull request. The action
resolves the ref it was called at and hands the SHA to the lint, which fails the
run when the crate's pin names a different one; where the ref cannot be resolved
the run says so rather than quietly checking nothing.

What the lint runs is [`validation.md`](adapter/validation.md).

## Every dependency is a commit SHA, and every pinned SHA is tagged

In a crate, a pin is a full 40-character commit SHA, never a branch name, a tag
or "latest"; the `uses:` ref that calls the lint is a tag on that same commit.
Without a pin, a consumer silently tracks whatever is on `main`, so a run that
passed yesterday can pass today for a different reason.

A tag is what keeps the commit reachable, because a branch tip is not a
guarantee. A tag holds the object even if the branch it sat on is later reset or
rebased, which would otherwise leave every CI run — including runs of unrelated
pull requests — dying at `git checkout` on an object that has been
garbage-collected. Do not pin a SHA that no tag points at.

So: **every commit of this repository that anything pins is tagged in this
repository**, verified with `git ls-remote` before the pin lands, and the same
obligation falls on any repository an adapter or a Bridge pins. A tag here is
annotated, so `git ls-remote <repository> 'refs/tags/<tag>^{}'` prints the
commit it points at, which is the SHA to pin; without `^{}` it prints the tag
object's own SHA. A pin to an untagged commit is not a pin; it is a bet on
nobody rewriting a branch. It applies to the `uses:` ref as much as to the SHA in
a crate: an action called at a branch is an action whose meaning changes without
a commit anywhere.

A pin is written as an entity, not a string: a `SoftwareSourceCode` with
`codeRepository` and `version`, which is the shape `bridge:specPin` and
`bridge:vocabularyPin` both use. The repository half is carried explicitly
because a commit that exists only on a fork must name the fork, or CI clones a
repository that does not hold the object. This specification's repository is
`https://github.com/jayostis/cascade-bridge-spec`; there is no other copy to pin.

## Pins move in the pull request that needs them

A pin is not swept forward on a schedule and is not synced to `main`. It moves
when a change needs what the new revision contains, in the pull request that
makes the change, and that pull request re-measures whatever the pin's numbers
are and records the before and after.

Why not sync to `main`: a suite pinned to a moving target passes today for a
different reason than it passed yesterday, and the difference is invisible.
Worse, the failure surfaces in whichever unrelated pull request happens to run
next, so the person who has to diagnose it is never the person who caused it.
The other extreme costs as much: measured counts that have gone stale against
the pin. A mandatory-verification section quoting numbers no run can reproduce
teaches the reader to disbelieve the section. Both failures are avoided by the
same rule: the pin and the measurement move together, in one deliberate commit.

## Nothing pins what it does not consume

A pin is a statement that this artefact reads that revision. An adapter pins one
revision of the Cascade vocabularies (`bridge:vocabularyPin`) because it always
writes at least one of them, and names only those it writes
(`bridge:vocabulary`): one that writes no `genomics:` term does not name the
genomics vocabulary. A Bridge that implements no profile an adapter requires
does not pin that adapter. Pins added
"for completeness" are pins nobody re-measures, and an unre-measured pin is a
stale fact with a SHA attached to make it look checked.

It is why this repository pins nothing at all. It writes no Cascade term, so it
consumes no vocabulary revision; it runs no adapter, so it consumes no adapter's
commit.

## A comparison is insensitive to everything the format does not mean

Not a pinning rule, but the same failure wearing different clothes: a contract
that asserts more than it means makes correct work fail, and the failure lands on
whoever runs it next rather than on whoever wrote it.

An RDF graph does not mean its blank node labels, and a findings array does not
mean its element order, so [`adapter/fixtures/manifest.md`](adapter/fixtures/manifest.md)
compares graphs up to relabelling and findings as a multiset. A stricter rule
than the format's meaning does not catch more mapping errors; it only fails
harnesses that are right.

## A Bridge's results flow as reports, not as pins

A Bridge's verdict on an adapter reaches a catalogue as an EARL report, never as
a pin in either direction: a Bridge pinning an adapter would be claiming
ownership of it, and an adapter pinning a Bridge would stop being portable. The
report's shape is [`engine/executing.md`](engine/executing.md).
