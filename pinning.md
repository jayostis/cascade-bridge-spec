# Pinning

## What knows about what

- **The specification knows only about itself.** It names no adapter and no engine.
- **An adapter pins the specification**, in its crate as `bridge:specPin`.
- **An engine pins the specification**, in its `compatibility.json`, having no crate.
- **An engine and an adapter know about each other only by saying so**, in a
  `compatibility.json` entry that blocks the merge when it does not hold
  ([`compatibility.md`](compatibility.md)).

**Why the specification names no one.** A check belongs with the thing it
checks. A specification that cloned adapters in CI would go red for a property
missing from somebody else's repository, would grow a job per adapter forever, and
would put diagnosis on whoever did not cause the failure. So every check is
published from here as an action, and runs in the adapter or the engine against
the head being proposed. The arrow still runs towards the specification.

## Pins move in the pull request that needs them

Not on a schedule. A suite pinned to a moving target passes today for a
different reason than yesterday, invisibly, and fails in whichever unrelated
pull request runs next. So the pin moves when a change needs the new revision,
in that change's pull request, which re-measures what the pin measures. A
default-branch pin in a `compatibility.json` is that rule applied: the pull
request records the standing choice.

**Changes flow downstream.** The specification merges first. A downstream pull
request may pin its feature branch meanwhile and swaps to the merge commit once
it lands. Nothing waits on a tag: a tag labels a commit that already passed.

**At merge time a pin is on the counterpart's default branch** (the rule is
`ready` in [`compatibility.md`](compatibility.md)), because a commit only on a
feature branch dies at `git checkout` the first time that branch is reset.

## Nothing pins what it does not consume

A pin says "this reads that revision". An adapter names only the Cascade
vocabularies it writes. A pin added for completeness is one nobody re-measures:
a stale fact with a SHA attached to make it look checked. This repository pins
nothing, because it writes no Cascade term and runs no adapter or engine.
