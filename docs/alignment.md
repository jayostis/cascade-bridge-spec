# Keeping the specification, the adapters and the Bridges aligned

Four repositories' worth of artefacts have to agree about which revision of
which vocabulary and which contract they were built against. RFC section 11
names the problem and stops short of a mechanism: "whatever repository layout is
chosen has to keep the pins visible and testable in CI." This document is the
mechanism.

## Dependencies point one way

```
spec  <-  adapter  <-  Bridge
```

- An **adapter** pins `spec` (the Cascade vocabularies it writes) and this
  specification. It knows nothing about any Bridge.
- A **Bridge** pins this specification, and it pins `spec` for the vocabularies
  its check and validate stages read. It knows about adapters only as inputs it
  is handed.
- **This specification** pins nothing downstream. It carries a catalogue of
  adapters, which is a list of things to validate, not a dependency.

The direction is the whole discipline. An adapter that pinned a Bridge would be
an adapter that runs on one Bridge, which is the opposite of what "an adapter is
data" is for; a specification that pinned an implementation would be a
specification the implementation could change.

This mirrors how `spec`, `conformance`, `sdk-typescript` and `cascade-cli`
already relate, and it is the "full separation" option of RFC section 15 rather
than either of the other two. The cost that option names is real and is accepted:
more repositories to keep in step.

## Every dependency is a commit SHA, and every pinned SHA is tagged

A pin is a full 40-character SHA, never a branch name, never a tag alone, never
"latest". `conformance/scripts/SPEC_PIN` is the existing statement of why:

> Without a pin the suite silently tracks whatever is on spec `main`, so a run
> that passed yesterday can pass today for a different reason.

And, on the tagging half:

> WHAT KEEPS THIS COMMIT REACHABLE, because a branch tip is not a guarantee: SIX
> tags point at this exact SHA ... A tag holds the object even if the fork's
> `main` is later reset or rebased onto upstream, which is the normal end of a
> fork workflow and would otherwise leave every CI run — including runs of
> unrelated PRs — dying at `git checkout` on an object that has been
> garbage-collected. Do not re-pin to a fork SHA that no tag points at.

So: **every commit of this repository that anything pins is tagged in this
repository**, verified with `git ls-remote` before the pin lands, and the same
obligation falls on any repository an adapter or a Bridge pins. A pin to an
untagged commit is not a pin; it is a bet on nobody rewriting a branch.

A pin is written as an entity, not a string: a `SoftwareSourceCode` with
`codeRepository` and `version`, which is the shape `bridge:specPin`,
`bridge:vocabularyPin` and a catalogue entry all use. The repository half is
carried explicitly for the reason SPEC_PIN gives about the fork: a commit that
exists only on a fork must name the fork, or CI clones a repository that does
not hold the object, and the pin moves back to the org in the same commit that
re-pins to an org SHA.

## Pins move in the pull request that needs them

A pin is not swept forward on a schedule and is not synced to `main`. It moves
when a change needs what the new revision contains, in the pull request that
makes the change, and that pull request re-measures whatever the pin's numbers
are and records the before and after.

Why not sync to `main`, stated the way conformance states it: a suite pinned to
a moving target passes today for a different reason than it passed yesterday,
and the difference is invisible. Worse, the failure surfaces in whichever
unrelated pull request happens to run next, so the person who has to diagnose it
is never the person who caused it. Conformance also shows the cost of the other
extreme — its measured counts had gone two pins stale, and "a
mandatory-verification section quoting numbers no run can reproduce teaches the
reader to disbelieve the section." Both failures are avoided by the same rule:
the pin and the measurement move together, in one deliberate commit.

## Nothing pins what it does not consume

A pin is a statement that this artefact reads that revision. An adapter that
writes no `genomics:` term does not pin the genomics vocabulary; a Bridge that
implements no profile an adapter requires does not pin that adapter. Pins added
"for completeness" are pins nobody re-measures, and an unre-measured pin is a
stale fact with a SHA attached to make it look checked.

## This repository's CI validates every catalogued adapter at its pinned commit

[`catalog/adapters.ttl`](../catalog/adapters.ttl) lists each known adapter with
its `schema:codeRepository` and the `schema:version` this specification
validates it at. CI clones each at that SHA and runs
[`scripts/validate-adapter.py`](../scripts/validate-adapter.py) against it, so a
change to the shapes that would break a real adapter fails here, in the pull
request that makes it, rather than in that adapter's repository weeks later.

The catalogue entry's SHA is itself a pin and moves under the same rule: in the
pull request that needs it. An adapter's own release does not move it; someone
adds a commit here, CI re-validates at the new SHA, and the move is reviewable.

## A Bridge's results flow to the catalogue as reports, not as a pin

RFC section 11 measures an adapter's tier by running its fixtures on every
published Bridge. That measurement must not become a pin in either direction: a
Bridge that pinned an adapter would be claiming ownership of it, and an adapter
that pinned a Bridge would stop being portable.

It flows as **EARL** instead — one `earl:Assertion` per manifest entry, with
`earl:test` the entry's IRI, `earl:subject` the Bridge and `earl:outcome` — which
is how every W3C test suite records implementation results. A tier is then a
query over the reports the catalogue holds: which Bridges passed which adapter's
manifest, at which revisions of each. Nobody declares it, this repository does
not compute it from an adapter's own files, and a lint may say only
`universal candidate` ([`validation.md`](validation.md)).

No Bridge is published, so the catalogue holds no reports and no adapter has a
measured tier. That is the honest state, and it is why the catalogue records only
repository, commit and required profiles today.

## In one paragraph

Dependencies point one way. Every dependency is a SHA. Every pinned SHA is
tagged. Pins move in the pull request that needs them, with the measurement
re-run in the same commit. Nothing pins what it does not consume. This
repository's CI proves each catalogued adapter still validates at its pin. And a
Bridge's verdict on an adapter reaches the catalogue as a report, never as a pin.
