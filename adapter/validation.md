# Validating an adapter package

What a conforming adapter package must satisfy, as **an RO-Crate profile**:
`cascade-bridge-adapter`, which declares itself `prof:isProfileOf` RO-Crate 1.2.
So an adapter is validated as an RO-Crate and as an adapter in one pass, against
one report, by `rocrate-validator` —
[`scripts/validate-adapter.py`](../scripts/validate-adapter.py) runs that profile
and prints what it found, and is what the published action
([`.github/actions/validate-adapter`](../.github/actions/validate-adapter/action.yml))
runs.

The requirements below are this specification's. Everything RO-Crate 1.2 requires
is inherited and is not restated here.

**A requirement is met or it is not, and any unmet requirement fails the run.**
Two consequences worth stating, because they are what a lint gets wrong:

- **A check that could not run reports an unmet requirement**, not silence. A
  machine without `lxml` has not satisfied the schema requirement; it never asked
  the question, and reporting nothing would let the silence read as an answer.
- **A check that ran and found nothing of its kind reports nothing.** An adapter
  whose manifest holds only `bridge:InputOnlyTest` entries has no expected graph,
  and has broken no rule: that type exists for exactly that case. There is
  nothing for its author to do, so there is nothing to say.

The one exception to the first is a package this lint has nothing against and
cannot read — a source schema declared JSON, which v1-draft does not specify.
That is a gap in the lint, not a fault in the package, and it is not reported as
a failure.

**Nothing an adapter names is fetched.** Digests are recomputed over the
committed bytes, and no publisher's file or referenced dataset is downloaded.
The tools do use the network, starting with the RO-Crate context the crate names.

What each requirement reports, in its own words, is
[`scripts/unittest-lint.py`](../scripts/unittest-lint.py): one test per decision,
each named for the sentence it asserts.

## The requirements

RO-Crate 1.2 conformance comes first, inherited: an adapter package is an
RO-Crate before it is anything else, and the profile says so rather than this
list repeating it.

Each is one file under [`profile/must/`](profile/must/).

A package that meets all of them, and RO-Crate 1.2's own, is a conforming
adapter package. None of them runs a mapping or compares a graph: that is the
test manifest, and it needs a Bridge ([`fixtures/manifest.md`](fixtures/manifest.md)).

## The media types an adapter package may declare

The allowed set is the `sh:in` list on `<#DescribedFile>` in
[`shapes/bridge.shapes.ttl`](../shapes/bridge.shapes.ttl), and a run that trips
on it prints the whole set in the violation. That is the set; it is not copied
here, because a copy is how a package comes to declare a media type the shapes
reject.

The set is deliberately short, and it is where "no code" is enforced. A format an
adapter needs and this set lacks is a pull request here, argued once, rather than
a media type invented in one adapter's crate. `encodingFormat` is a string rather
than a PRONOM IRI: RO-Crate 1.2 allows either, and a set of two spellings is a
set that can disagree with itself.

## The specification pin

The pin is read and compared with nothing: the starter checks this repository
out at exactly the commit it names before the lint runs, so the revision running
is the pinned one by construction. Whether that commit is on this repository's
default branch is a merge-time question, and the merge gate asks it: `ready`, in
[`../compatibility.md`](../compatibility.md).

## The lint as a reusable action

The checks are published as a composite GitHub Action,
`.github/actions/validate-adapter`, for the reason in
[`../pinning.md`](../pinning.md). An adapter's CI does not call it directly. It
calls the starter, at a tag that never moves:

```yaml
jobs:
  adapter:
    runs-on: ubuntu-latest
    steps:
      - uses: jayostis/cascade-bridge-spec/.github/actions/start@start-v1
  ready-to-merge:
    runs-on: ubuntu-latest
    steps:
      - uses: jayostis/cascade-bridge-spec/.github/actions/start@start-v1
        with:
          check: ready-to-merge
```

That is the whole of it: two jobs, the second the merge gate, meant to be a
required status check. Bumping the pin is an edit to the crate and nothing else.
What the starter reads, checks out and hands over to is
[`../compatibility.md`](../compatibility.md).

## Running it

```bash
python3 -m pip install pyshacl rdflib roc-validator lxml
python3 scripts/validate-adapter.py <path to an adapter checkout>
```

Exit status is 0 when every requirement is met and 1 when any is not. CI on
this project's repositories is Linux and invokes `python3` directly;
do not commit a machine-specific way of running it.

