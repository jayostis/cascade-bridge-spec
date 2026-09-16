# Validating an adapter package

What a conforming adapter package must satisfy is an RO-Crate profile,
[`profile/`](profile/), a profile of RO-Crate 1.2: `rocrate-validator` checks an
adapter against both in one pass. What RO-Crate 1.2 requires is not restated here.

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

What each requirement reports is [`tests/adapter_profile/`](../tests/adapter_profile/).

## The requirements

Each is one file under [`profile/must/`](profile/must/).

A package that meets all of them, and RO-Crate 1.2's own, is a conforming
adapter package. None of them runs a mapping or compares a graph: that is the
test manifest, and it needs a Bridge ([`fixtures/manifest.md`](fixtures/manifest.md)).

## The media types an adapter package may declare

The allowed set is the `sh:in` list in
[`profile/must/media_types.ttl`](profile/must/media_types.ttl), and a run that trips
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
rocrate-validator validate <adapter> \
  --extra-profiles-path <this repository>/adapter \
  --profile-identifier cascade-bridge-adapter --no-paging --verbose
```

