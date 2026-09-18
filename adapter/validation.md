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
on:
  push:
    branches: [main]
  pull_request:
    types: [opened, synchronize, reopened, edited]
  workflow_dispatch:

permissions:
  contents: read
  pull-requests: write

jobs:
  adapter:
    runs-on: ubuntu-latest
    steps:
      - uses: jayostis/cascade-bridge-spec/.github/actions/start@main
  ready-to-merge:
    runs-on: ubuntu-latest
    steps:
      - uses: jayostis/cascade-bridge-spec/.github/actions/start@main
        with:
          check: ready-to-merge
```

Make both jobs required status checks. `edited` is what starts a run when a
description's `Depends-On:` lines change, and `pull-requests: write` is what the
action posts the table with, in a step of its own: the checks are the version the
run picked — a named pull request's own code, where one is named — and are given
no token. On a pull request from a fork the token is read-only whatever the
workflow asks for, and the run says so rather than failing.
