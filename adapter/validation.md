# Validating an adapter package

An adapter package conforms when `rocrate-validator` passes it against RO-Crate
1.2 and [`profile/`](profile/). Each requirement is one file in
[`profile/must/`](profile/must/), and what it reports is its test in
[`../tests/adapter_profile/`](../tests/adapter_profile/).

```bash
python3 -m pip install --group <this repository>/pyproject.toml:validators
rocrate-validator validate <adapter> \
  --extra-profiles-path <this repository>/adapter \
  --profile-identifier cascade-bridge-adapter --no-paging --verbose
```

**A check that could not run fails.** Silence must not read as a pass. The one
exception is a source schema declared JSON, which v1-draft does not specify: a
gap in the lint, not a fault in the package.

**Nothing an adapter names is fetched.** Digests are recomputed over committed
bytes only.

**The media type set is short on purpose**: it is where "no code" is enforced.
A format it lacks is a pull request here, not a media type invented in one
adapter.

## In CI

An adapter's CI calls the starter, at a tag that never moves. Bumping the spec
pin is an edit to the crate and nothing else:

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

The second job is the merge gate, meant to be a required status check
([`../compatibility.md`](../compatibility.md)).
