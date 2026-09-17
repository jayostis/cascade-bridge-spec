# Validating an adapter package

An adapter package conforms when `rocrate-validator` passes it against RO-Crate
1.2 and [`profile/`](profile/). Each requirement is a file in
[`profile/must/`](profile/must/), and what it reports is its test in
[`../tests/adapter_profile/`](../tests/adapter_profile/).

```bash
python3 -m pip install --group <this repository>/pyproject.toml:validators
rocrate-validator validate <adapter> \
  --extra-profiles-path <this repository>/adapter \
  --profile-identifier cascade-bridge-adapter --no-paging --verbose
```

Nothing an adapter names is fetched. A media type the profile does not allow is
a pull request here, not one invented in an adapter.

## In CI

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

Make `ready-to-merge` a required status check. Bumping the spec pin is an edit
to the crate alone.
