# Keeping the specification, the adapters and the Bridges aligned

Several repositories' worth of artefacts have to agree about which revision of
which vocabulary and which contract they were built against. RFC section 11
names the problem and stops short of a mechanism: "whatever repository layout is
chosen has to keep the pins visible and testable in CI." This document is the
mechanism.

## What knows about what

```
specification  <-  adapter  <-  Bridge
        \             |            /
         `------->  catalogue  <--'
```

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

This mirrors how `spec`, `conformance`, `sdk-typescript` and `cascade-cli`
already relate, and it is the "full separation" option of RFC section 15 rather
than either of the other two. The cost that option names is real and is accepted:
more repositories to keep in step.

### The specification does not know which adapters exist

At 0.1.0 this repository carried `catalog/adapters.ttl`, naming one adapter, its
repository and a commit of it, and a CI job that cloned that repository at that
commit and validated it. Both were removed at 0.2.0, because both point upward.

The consequence was not theoretical. This repository's CI was red on a property
missing from somebody else's repository. With fifty adapters it would clone fifty
repositories on every push and go red whenever any of them broke, and the person
who had to diagnose a failure would never be the person who caused it. An adapter
can live on any account in any organisation, and the specification should not
need to know one exists in order for the specification to be checkable.

What replaced it is in the next section: the check moved to the adapter, where
the thing being checked lives, and runs against the head being proposed rather
than against a snapshot this repository remembered.

### The catalogue is a repository of its own, and it does not exist

RFC section 9 asks for one: "the tier is recorded where adapters are published.
That means a catalog, however minimal, because 'universal' is a claim someone has
to be able to look up and re-verify." That is still wanted. It is downstream of
every adapter and every Bridge, it holds the EARL reports a Bridge produces, and
a tier is a query over them. It is warranted when more than one adapter exists
and at least one Bridge is producing results, and none of that is true yet.
Nothing about it belongs here.

## An adapter's CI calls this repository's lint

The lint is published from here as a composite GitHub Action,
[`.github/actions/validate-adapter`](../.github/actions/validate-adapter/action.yml).
An adapter's whole CI is:

```yaml
      - uses: actions/checkout@v4
      - uses: jayostis/cascade-bridge-spec/.github/actions/validate-adapter@v0.3.0
```

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

What the lint runs is [`validation.md`](validation.md).

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
untagged commit is not a pin; it is a bet on nobody rewriting a branch. It
applies to the `uses:` ref as much as to the SHA in a crate: an action called at
a branch is an action whose meaning changes without a commit anywhere.

A pin is written as an entity, not a string: a `SoftwareSourceCode` with
`codeRepository` and `version`, which is the shape `bridge:specPin` and
`bridge:vocabularyPin` both use. The repository half is carried explicitly for
the reason SPEC_PIN gives about the fork: a commit that exists only on a fork
must name the fork, or CI clones a repository that does not hold the object, and
the pin moves back to the org in the same commit that re-pins to an org SHA.

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

It is why this repository pins nothing at all. It writes no Cascade term, so it
consumes no vocabulary revision; it runs no adapter, so it consumes no adapter's
commit.

## A comparison is insensitive to everything the format does not mean

Not a pinning rule, but the same failure wearing different clothes: a contract
that asserts more than it means makes correct work fail, and the failure lands on
whoever runs it next rather than on whoever wrote it.

An RDF graph does not mean its blank node labels, so
[`test-manifest.md`](test-manifest.md) relabels them before comparing. A JSON
array of findings does not mean its element order, so it is compared as a
multiset. That second rule replaced an ordering requirement at 0.2.0, and the
measurement is worth keeping: the pilot adapter's committed sidecars were written
by a script sorting with ICU collation, in which `/` precedes `@` although U+002F
is above U+0040, and 78, 56, 6 and 1 adjacent pairs across the four files are out
of code-point order. A harness comparing with Java's `String.compareTo` or with
JavaScript's `<` would have reported a false failure on a correct mapping. A
stricter rule than the format's meaning does not catch more mapping errors; it
only fails harnesses that are right.

## A Bridge's results flow to a catalogue as reports, not as a pin

RFC section 11 measures an adapter's tier by running its fixtures on every
published Bridge. That measurement must not become a pin in either direction: a
Bridge that pinned an adapter would be claiming ownership of it, and an adapter
that pinned a Bridge would stop being portable.

It flows as **EARL** instead — one `earl:Assertion` per manifest entry, with
`earl:test` the entry's IRI, `earl:subject` the Bridge and `earl:outcome` — which
is how every W3C test suite records implementation results. A tier is then a
query over the reports a catalogue holds: which Bridges passed which adapter's
manifest, at which revisions of each. Nobody declares it, no adapter computes it
from its own files, and a lint may say only `universal candidate`
([`validation.md`](validation.md)).

No Bridge is published and no catalogue exists, so there are no reports and no
adapter has a measured tier. That is the honest state.

## In one paragraph

The specification knows about itself; an adapter and a Bridge know about the
specification; a catalogue knows about all of them and nothing knows about it.
Every dependency is a SHA, every pinned SHA is tagged, and an adapter's `uses:`
ref and its `bridge:specPin` name the same commit. Pins move in the pull request
that needs them, with the measurement re-run in the same commit. Nothing pins
what it does not consume. A comparison is insensitive to everything the format
does not mean. And a Bridge's verdict on an adapter reaches a catalogue as a
report, never as a pin.
