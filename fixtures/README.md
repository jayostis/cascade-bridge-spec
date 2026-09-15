# Fixtures

The subjects this repository's machinery is run against.

```
synthetic-adapter/   a synthetic adapter package: the lint's own test subject
lift/                the lift vectors a sparql-1.1 Bridge must reproduce
```

The lift vectors are an engine's subject rather than the lint's: each is an XML
document and the N-Triples its lift must be isomorphic to, listed in
`lift/manifest.ttl` as `bridge:LiftTest` entries
([`../engine/sparql.md`](../engine/sparql.md)). The rest of this file is about
the synthetic adapter.

## Why a synthetic package and not a real adapter

`scripts/validate-adapter.py` is published as
[`.github/actions/validate-adapter`](../.github/actions/validate-adapter/action.yml)
for an adapter repository's CI to call at a tag. A lint published untested is a
lint nobody should trust, so it has to run somewhere on every change here — and
the one thing it must not run against is a real adapter.

**This repository must not know that any adapter exists**
([`pinning.md`](../pinning.md) says why). A real adapter here — as a
submodule, a clone, a pinned SHA or a name in a workflow — is that bug wearing
a fixture's clothes.

A package this repository wrote itself is the way out. It is a subject this
repository owns, it changes only when someone here changes it, and it names no
adapter.

## What is in it, and what is invented

Everything. The format, its two schemas, its records, its release and its
vocabulary are made up; every URL that is not this repository's own is under
`example.org`, IANA's reserved example domain, and none of them resolves. No
real format, publisher, dataset or adapter is named anywhere in it.

It is minimal, and every part of it earns its place by covering a branch of the
seven checks in [`adapter/validation.md`](../adapter/validation.md) that a
single real adapter would not cover at once:

| what it holds | the branch it covers |
|---|---|
| two envelopes, one with a `bridge:documentSchema` and one without | check 5 takes the envelope's schema where there is one and falls back to the adapter's `bridge:sourceSchema` where there is not |
| a file carrying only a `sha256` | check 4's local claim: these bytes, here, now |
| two files carrying a `sha256` and an `md5` | check 4's publisher's claim, recomputed and reported as a different finding from a wrong `sha256` |
| a referenced release under `example.org` | a digest on bytes that are not committed: recorded, not compared, and never fetched |
| an isomorphic conversion test | check 6 has an expected graph to parse |
| an input-only test | a test with no `mf:result`, which judges nothing |
| a dataset completion test | check 5 meets a test whose bytes are not here, and says so instead of counting it validated |
| a mapping, a findings query and a detect query, requiring `sparql-1.1` | the queries check 2 requires of every adapter and check 7 parses; the mapping and the findings query produce the expected graph and findings from `example-0001.xml` |

## The specification pin

The one entity in the crate that names something real is `bridge:specPin`:
`jayostis/cascade-bridge-spec` at the commit released as v0.2.0.

That is a commit on this repository's default branch, as every merged pin must
be, and not a revision the package conforms to. The package conforms to the shapes in its own commit, and a
package inside this repository cannot pin a release that contains it, so its
pin can only name an earlier tag, whose shapes it need not satisfy. Nothing
moves the pin when a release is tagged, because nothing compares it: CI calls
the action by local path, so there is no ref to resolve and the run reports the
pin without comparing it — which is itself one of the states the lint has to be
seen reporting.

## Seeing the lint fail

`scripts/selftest-lint.py` copies this package into a temporary directory,
breaks one property per case, and asserts what the lint says about it:

```bash
python3 -m pip install pyshacl rdflib roc-validator lxml
python3 scripts/selftest-lint.py
```

Fourteen cases: the package unbroken passing, and one red case each for a crate
that names no mapping, a query declared with the wrong media type, a crate that
does not require `sparql-1.1`, an undescribed file, a wrong local `sha256`, a
wrong publisher `md5`, an input that does not satisfy its schema, a schema
language the lint does not read, an expected graph that is not Turtle, a
manifest that names no expected graph, a query that does not parse, a query of
the wrong form, and a findings query projecting the wrong variables. The schema
language the lint does not read, and the manifest that names no expected graph,
exit 0 on purpose: `not run` and `nothing to check` are not failures, and the
case asserts that the lint says them in their own words rather than reporting a
pass.

Nothing tracked is mutated, and no mutated copy is ever written inside the
repository.

## Changing it

A change to the shapes, the vocabulary or the media-type set changes what this
package must look like. Change it in the same commit, run the lint against it,
run the selftest, and — because a fixture cannot tell you what it breaks in the
wild — run the lint by hand against a real adapter checkout beside this one,
saying in the commit which adapter and at which commit, without adding it to
this repository in any form (`../shapes/CLAUDE.md`).

The digests in the crate are recorded over the committed bytes. Editing a file
here without restating its `sha256` and `contentSize` in the same commit fails
check 4, which is the check doing its job.
