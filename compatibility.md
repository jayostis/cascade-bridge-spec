# Compatibility between engines and adapters

An engine commits a `compatibility.json` at its root, and an adapter may, naming
the adapters (in an engine) or engines (in an adapter) it must pass with.
**Every entry that does not hold blocks the merge.**

Its keys are [`vocab/compatibility.context.jsonld`](vocab/compatibility.context.jsonld),
each a `bridge:` term in [`vocab/bridge.ttl`](vocab/bridge.ttl), checked by the
compatibility shapes in [`shapes/bridge.shapes.ttl`](shapes/bridge.shapes.ttl).
An engine's file:

```json
{
  "@context": "https://ns.cascadeprotocol.org/bridge/v1-draft/compatibility.jsonld",
  "setup": ["npm", "ci"],
  "command": ["node", "packages/bridge-cli/src/cli.ts"],
  "mustPassWith": ["https://github.com/example-org/example-adapter"]
}
```

An adapter's file has only `mustPassWith`.

## Which version of each repository a run uses

Picked when the run starts, as Zuul checks out a job's required projects
([project gating](https://zuul-ci.org/docs/zuul/latest/gating.html),
[job configuration](https://zuul-ci.org/docs/zuul/latest/config/job.html)):

- the open pull requests reached by `Depends-On:` lines, from the description of
  the pull request under test and then from each named pull request's own, each
  merged into the branch it targets;
- otherwise the branch named like the branch the run is on: the branch the pull
  request under test targets, or the one a push, manual or scheduled run is on;
- otherwise the default branch.

A local run uses every sibling checkout as it is on disk, uncommitted edits
included.

Descriptions are read without credentials, so every repository a run reads must
be public, and the reads a run makes share GitHub's hourly allowance for the
address it runs from.

A pull request merges only once every pull request it names directly has merged.

**A `Depends-On:` line goes one way**, as in Zuul without
[circular dependencies](https://zuul-ci.org/docs/zuul/latest/config/queue.html).

## Where this departs from Zuul

GitHub Actions cannot reproduce these, so a person or an agent does it by hand:

- **A named pull request changing retests nothing.** Rerun the dependent pull
  request's workflow: `gh run rerun`.
- **There is no gate queue**, so a pass is as fresh as its last run and the
  branches under it can move after it. Rerun `compatibility` and
  `ready-to-merge` before merging; a run says so when it used a named pull
  request. Nothing pins a counterpart either, so a pass on a default branch
  goes stale the same way, and the caller's nightly run is what notices.
- **A repository's state is not frozen across a run's jobs**, so two checks of
  one pull request can read different descriptions and branches. Rerun both
  rather than trusting a mixed pair.
- **A cycle is refused rather than merged as one unit.** Split the change into
  backward-compatible steps, each leaving every default branch green.
- **A pull request named in the repository under test is merged into nothing**,
  which its row says: the run checks that repository out as the pull request
  under test, and the merge gate still holds this one until that one merges.
  Land it first, or fold its changes into this pull request.

These are chosen, and could be otherwise:

- **A named pull request's specification runs**, rather than being read as data:
  the entry point hands the run to the version it picked, which is how a change
  here is tried before it merges, and is how Zuul treats an
  [untrusted project's](https://zuul-ci.org/docs/zuul/latest/concepts.html) job
  content rather than a config project's. Review a pull request here as code
  that will run in every repository whose pull request names it. It is handed no
  token there: `.github/actions/start`, which the caller names at `@main` and
  which no run replaces, posts the table itself, from the workflow's own context
  rather than anything the run leaves behind. A run and that step share a
  runner, so this is a boundary and not a sandbox.
- **Nothing here starts a run anywhere else**, because this repository knows of
  no adapter and no engine. A change to what an adapter or a Bridge must do is
  tried from a no-op pull request in one, naming this one on a `Depends-On:`
  line, before it merges.
- **The merge gate reads the pull requests named directly**, and each of those
  is held by its own repository's gate, so a chain merges from its end.
- **A named pull request closed without merging fails the check** rather than
  taking the dependent out of the queue. Cut the `Depends-On:` line; editing the
  description starts a run.
- **A counterpart is named by the repository under test**, not by a tenant, and
  not transitively: what a counterpart itself must pass with is its own run's
  business.
- **A run is aimed at no version.** There is no `override-checkout`; to try a
  branch, cut one of the same name in each repository.

## The tooling

[`scripts/compatibility.py`](scripts/compatibility.py); its docstring is the
usage. A repository's CI calls only `.github/actions/start@main`. A pull
request here that changes the tooling is tried first from a no-op engine or
adapter pull request naming it on a `Depends-On:` line. A caller depends on no
more than the entry point's path, its arguments, the results directory and the
`table.md` it writes there: those names reach a caller only once they have
merged, and everything else the run does comes from the version it picked.

## The workflow an adapter and an engine both run

```yaml
on:
  push:
    branches: [main]
  pull_request:
    types: [opened, synchronize, reopened, edited]
  schedule:
    - cron: '17 3 * * *'
  workflow_dispatch:

permissions:
  contents: read
  pull-requests: write

jobs:
  compatibility:
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

Make both jobs required status checks, and keep whatever you have named them: a
renamed job leaves every merge waiting on a check that never reports. `edited` is what starts a run
when a description's `Depends-On:` lines change, and `pull-requests: write` is
what the action posts the table with, in a step of its own: the checks are the
version the run picked — a named pull request's own code, where one is named —
and are given no token. On a pull request from a fork the token is read-only
whatever the workflow asks for, and the run says so rather than failing.
