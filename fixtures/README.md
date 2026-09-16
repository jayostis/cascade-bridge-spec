# Fixtures

The subjects this repository's machinery is run against.

```
synthetic-adapter/   a synthetic adapter package: the lint's own test subject
fake-engine/         an engine that honours the command contract and runs nothing
lift/                the lift and envelope-skeleton vectors a sparql-1.1 Bridge must reproduce
```

The fake engine is `scripts/selftest-compatibility.py`'s counterpart to the
synthetic adapter: it takes `test <adapter directory> --earl <file>`
([`../engine/command.md`](../engine/command.md)) and writes a canned EARL
report, so that judging a report is exercised without this repository running, or
naming, a real engine. Its exit status is 0 whatever it reports, so that a case
whose report says `failed` still exercises the rule in
[`../engine/command.md`](../engine/command.md).

The lift vectors are an engine's subject rather than the lint's: each is an XML
document and the N-Triples a Bridge must produce from it, listed in
`lift/manifest.ttl` ([`../engine/sparql.md`](../engine/sparql.md)) — the lift
itself, and the envelope skeleton a detect query is evaluated over, which is the
one the vectors are here to pin down. The rest of this file is about the
synthetic adapter.

## Why a synthetic package and not a real adapter

`scripts/validate-adapter.py` is published as
[`.github/actions/validate-adapter`](../.github/actions/validate-adapter/action.yml)
for an adapter repository's CI to reach through the starter. A lint published untested is a
lint nobody should trust, so it has to run somewhere on every change here — and
the one thing it must not run against is a real adapter.

**This repository must not know that any adapter exists**
([`pinning.md`](../pinning.md) says why). A real adapter here — as a
submodule, a clone, a pinned SHA or a name in a workflow — is that bug wearing
a fixture's clothes.

A package this repository wrote itself is the way out. It is a subject this
repository owns, it changes only when someone here changes it, and it names no
adapter.

## What is in it

It is minimal, and every part of it earns its place by covering a branch of the
checks in [`adapter/validation.md`](../adapter/validation.md) that a single
real adapter would not cover at once: two envelopes for check 5's two ways of
finding a schema, three digest arrangements for check 4's local and publisher's
claims and for bytes that are not committed, one test of each type, and the three
queries checks 2 and 7 want.

Which branch each part is there for is the entity's own `description` in
`synthetic-adapter/ro-crate-metadata.json`. That is the copy a reader of the
package meets, and it is the one that moves when the package does.

## The specification pin

The one entity in the crate that names something real is `bridge:specPin`:
`jayostis/cascade-bridge-spec` at the commit released as v0.2.0.

That is a commit on this repository's default branch, as every merged pin must
be, and not a revision the package conforms to. The package conforms to the shapes in its own commit, and a
package inside this repository cannot pin a release that contains it, so its
pin can only name an earlier tag, whose shapes it need not satisfy. Nothing
moves the pin, because nothing needs it to: the lint reads a pin and compares it
with nothing, and CI calls the starter by local path, which runs the tools from
the checkout it is in rather than from the pinned commit. The merge gate does
run against the pin in CI, and holds, because the commit is on this
repository's default branch.

## Seeing the lint fail

`scripts/selftest-lint.py` copies this package into a temporary directory, breaks
one property per case, and asserts what the lint says about it. Its cases are the
list of what this package is able to show going wrong; read them there rather
than from a census here, which would be stale on the next one anyone adds. Two of
them exit 0 on purpose, because `not run` and `nothing to check` are not
failures.

Nothing tracked is mutated, and no mutated copy is ever written inside the
repository.

## Changing it

A change to the shapes, the vocabulary or the media-type set changes what this
package must look like. Change it in the same commit, run the lint against it,
run the selftest, and — because a fixture cannot tell you what it breaks in the
wild — do what `../shapes/CLAUDE.md` says about a real adapter checkout.

The digests in the crate are recorded over the committed bytes. Editing a file
here without restating its `sha256` and `contentSize` in the same commit fails
check 4, which is the check doing its job.
