# Compatibility between engines, adapters and runtimes

**Nothing pins the specification, an engine, an adapter, a runtime or a
vocabulary to a commit of another.** Each is tested against the others' default
branch, a change across them lands as pull requests paired by `Depends-On:`
lines, and a release records the commit of each repository it was tested with.

An engine commits a `compatibility.json` at its root, and an adapter may, naming
the adapters (in an engine) or engines (in an adapter) it must pass with, and an
engine names each host it ships to. **Every adapter that does not hold on a host
blocks the merge.** An engine under test also runs the library cases of
[`fixtures/library/`](fixtures/library/) on each of its hosts, through its
`library` command ([`engine/command.md`](engine/command.md)), and a host on which
they do not hold blocks the merge too, whatever its `mustPassWith` names.

Its keys are [`vocab/compatibility.context.jsonld`](vocab/compatibility.context.jsonld),
each a `bridge:` term in [`vocab/bridge.ttl`](vocab/bridge.ttl), checked by the
compatibility shapes in [`shapes/bridge.shapes.ttl`](shapes/bridge.shapes.ttl).
An engine's file:

```json
{
  "@context": "https://ns.cascadeprotocol.org/bridge/v1-draft/compatibility.jsonld",
  "host": [
    { "name": "native", "setup": ["cargo", "build", "--release"], "command": ["cargo", "run", "--release", "--"] },
    { "name": "node", "setup": ["sh", "hosts/node/setup.sh"], "command": ["node", "hosts/node/cli.mjs"] }
  ],
  "mustPassWith": ["https://github.com/example-org/example-adapter"]
}
```

A host may carry a `release`: `asset`, a glob naming one asset of the engine
repository's release tagged `build-<commit>`; `path`, where in the engine's
checkout it goes (an archive is unpacked there from its `package/` folder); and
`command`, run in place of the host's when it differs. When an adapter's run, in
CI on an x86_64 Linux runner, picks the engine at a commit with that release,
merges into it pull requests that change nothing but its `compatibility.json`,
or fast-forwards it to the head of a named pull request that has that release,
the asset is placed in place of the host's setup, once its bytes match a digest
the release's notes give (a `sha256-`, `sha384-` or `sha512-` integrity, or a
SHA-256 in hex). A missing release is waited for, up to 6 minutes, while a run
of the engine that a push or a pull request started at that commit is unfinished, unless the commit is the head of a
fork's pull request. Otherwise the setup runs.

An adapter's file has only `mustPassWith`.

A runtime is a repository holding `cascade-runtime.json`, which names the
vocabulary and each adapter it loads by repository: those are its counterparts.
Its `compatibility.json` names its hosts, as an engine's does, and no
`mustPassWith`. On each host the run appends `--report <file>` to the host's
command, then `--folder <repository>=<folder>` for each repository
`cascade-runtime.json` names, keyed as that file writes it. The command is also
given `CASCADE_PULL_REQUESTS`, the path of a JSON file (`{}` in a local run)
holding every pull request the run read, as it read them with its token: keyed
`owner/repository/pull/N`, each with its `body`, `state`, `merged`, and `base`
and `head` (`ref`, `sha` and `repo.full_name`), or `null` where it could not read
one. The command holds no token (the run empties `GITHUB_TOKEN` and `GH_TOKEN`
for everything it starts), so this file is how it reads the pull requests that
pick what it reads from no checkout, the Bridge's build. The command runs the
vocabulary's conformance kit there and writes an EARL report, which is judged by
[`engine/faults-of-a-report.rq`](engine/faults-of-a-report.rq) on its outcomes
alone: no manifest says which entries it must hold. **A host on which it does not
hold blocks the merge.**

A vocabulary is a repository holding a crate whose root is no `bridge:Adapter`,
as [`jayostis/cascade-vocabulary`](https://github.com/jayostis/cascade-vocabulary)
does. Its `compatibility.json` has only `mustPassWith`, naming runtimes. Each is
picked as a counterpart is, and its conformance command run as a runtime under
test's is, with the vocabulary under test handed in for the one it names and each
adapter it names picked as a counterpart is. **A runtime whose report does
not hold blocks the merge.** A change a runtime must follow lands as a pair: the
vocabulary's pull request and the runtime's, each naming the other on a
`Depends-On:` line.

A runtime reads the Bridge as a package the Bridge publishes as the release
`build-<commit>`, for every commit of its default branch and every head of a pull
request from the Bridge's repository itself; the run builds nothing of it, and
the runtime says which build it read and how it picked it. A `cascade-bridge-rs`
checkout beside the runtime, or handed in with `--folder`, has its own build used when it was made from the
checkout as it is, else the release of the commit the checkout is at; a checkout
with uncommitted files and no build of them stops the run. Otherwise one rule
applies, with no fall-through to the next once it has picked: the head of an open
Bridge pull request reached by `Depends-On:` lines (below), read at that head
alone, unmerged, where a counterpart's is merged into its target; else the head of
the Bridge's branch named like the branch the run is on, unless that is its
default branch; else the newest of the last 100 commits of its default branch
with a build, which is also the pick of a local run with no checkout. A picked
commit with no build stops the run, saying how it was picked. A runtime refuses
two Bridge pull requests named, one from a fork (only the Bridge's own get a
build) and one closed without merging; it stops on a `Depends-On:` line naming no
pull request and on a named Bridge pull request it cannot read, and passes over
one elsewhere it cannot read, as the run does.

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

The vocabulary repository an adapter's `bridge:cascadeVocabularyRepository`
names, and each repository a runtime's `cascade-runtime.json` names, is picked
as a counterpart is.

The repository under test is the checkout of the pull request under test, with
the head of each pull request of that repository reached the same way, open or
merged since, merged into it in the order of their numbers, as Zuul tests a
change with those ahead of it: a cycle within one repository is tested as the
set that will land. One closed without merging, one targeting another branch,
or one that does not merge cleanly into what is merged before it, fails the
check.

A local run uses every sibling checkout as it is on disk, uncommitted edits
included, the vocabulary repository among them, in the folder named as that
repository, and no option changes that.

Every repository a run reads must be public. Every read of GitHub's API is made
with the job's token, which `.github/actions/start` passes unless the caller
gives it another, so a run is held to that token's allowance and not to the one
GitHub gives an address without credentials.

A pull request merges only once every pull request it names directly has merged,
or names it back, directly or through others, and has passed every check but its
own merge gate, counting only the latest run of each check. A cycle merges only
once every pull request it names outside itself has merged. While a member's
checks are still running and none has failed, the gate waits for them, for a
time well over a run, so the members' gates pass without a rerun once every
member's checks have. Pull requests naming each other are how a breaking change
across an engine and an adapter lands, as Zuul's
[circular dependencies](https://zuul-ci.org/docs/zuul/latest/config/queue.html)
allow.

## Where this departs from Zuul

GitHub Actions cannot reproduce these, so a person or an agent does it by hand:

- **A named pull request changing retests nothing.** Rerun the dependent pull
  request's workflow: `gh run rerun`.
- **There is no gate queue**, so a pass is as fresh as its last run and the
  branches under it can move after it. Rerun `compatibility` and
  `ready-to-merge` before merging; a run says so when it used a named pull
  request. A pass on a default branch goes stale the same way, and the
  caller's nightly run is what notices.
- **A repository's state is not frozen across a run's jobs**, so two checks of
  one pull request can read different descriptions and branches. Rerun both
  rather than trusting a mixed pair.
- **A person merges a cycle's pull requests one after another**, and a default
  branch is red between the first merge and the last.
- **A cycle's members give their merge gate the same check name**, as
  [the workflow an adapter and an engine both run](#the-workflow-an-adapter-and-an-engine-both-run)
  does (`ready-to-merge`): each gate discounts that check on the others.
- **A Bridge pull request is built by the Bridge, not by the run, and read at
  its head alone.** The run lists one named on a `Depends-On:` line as not used,
  because it checks the Bridge out nowhere; the runtime reads the `build-<head>`
  pre-release the Bridge published for that pull request's head, unmerged with
  the branch it targets. A picked commit with no build stops the run, saying how
  it was picked.
- **A runtime does not wait for a Bridge publish in progress**, as the run waits
  for an engine's release. Rerun the runtime's pull request once the Bridge's
  publish run has made `build-<head>`. The Bridge prunes a pull request's older
  builds when it moves to a new head, merges or closes, so a rerun also picks
  again past a build pruned under it.
- **A re-run keeps the run's commit.** After a retarget, a pull request is still
  tested merged into its old base, while counterparts follow the new one. Push,
  or run `gh pr update-branch`, for a fresh merge.
- **On a pull request from a fork, whose token is read-only, an edit re-runs
  nothing.** The run says so and names the command: `gh run rerun`.
- **A red `rerun-when-edited` does not block a merge.** When the re-run fails,
  only that job goes red: `compatibility` can stay green on the old run, stale,
  and `rerun-when-edited` is not a required check (a skipped job passes, and a
  later green one hides the red). Run the command the failed job names, or
  `gh run rerun <id> -R <repository>`, and merge only once the re-run has passed.
- **A change to which pull requests a run follows is tried once it has merged.**
  The default branch's copy follows them to pick the version, before that version
  runs anything, so a run refuses on the rules of the day whatever a pull request
  proposes. What it would newly accept is reachable only from the default branch.

These are chosen, and could be otherwise:

- **A named pull request's specification runs**, rather than being read as data:
  the entry point hands the run to the version it picked, which is how a change
  here is tried before it merges, and is how Zuul treats an
  [untrusted project's](https://zuul-ci.org/docs/zuul/latest/concepts.html) job
  content rather than a config project's. Review a pull request here as code
  that will run in every repository whose pull request names it, holding that
  repository's job token. It posts nothing: `.github/actions/start`, which the caller names at `@main` and
  which no run replaces, posts the table itself, from the workflow's own context
  rather than anything the run leaves behind. The token reaches the entry point
  of the version picked, to read GitHub's API with, and nothing that entry point
  starts. A run and that step share a runner, so this is a
  boundary and not a sandbox.
- **A re-run is decided by the action at the ref the caller named**, in a job
  that holds `actions: write` and runs nothing the run picked, not by the
  version the run picks. A change to it is tried from a caller naming
  `rerun-when-edited@<branch>`, not from a `Depends-On:` line.
- **Nothing here starts a run anywhere else**, because this repository knows of
  no adapter and no engine. A change to what an adapter or a Bridge must do is
  tried from a no-op pull request in one, naming this one on a `Depends-On:`
  line, before it merges.
- **The merge gate waits on the pull requests named directly**, and each of those
  is held by its own repository's gate, so a chain merges from its end.
- **A named pull request closed without merging fails the check** rather than
  taking the dependent out of the queue. Cut the `Depends-On:` line; editing the
  description starts a run.
- **A counterpart is named by the repository under test**, not by a tenant, and
  not transitively: what a counterpart itself must pass with is its own run's
  business.
- **A run is aimed at no version.** There is no `override-checkout`. A pull
  request matches the branch it *targets*, so cutting one name in each
  repository pairs nothing while the work is in review: name each pull request
  the others need on a `Depends-On:` line instead.

## The tooling

[`scripts/compatibility.py`](scripts/compatibility.py); its docstring is the
usage. A repository's CI calls only `.github/actions/start@main`. A pull
request here that changes the tooling is tried first from a no-op engine or
adapter pull request naming it on a `Depends-On:` line. A caller depends on no
more than the entry point's path, its arguments, the results directory and the
`table.md` it writes there: those names reach a caller only once they have
merged, and everything else the run does comes from the version it picked.
A job that needs only the counterparts a `Depends-On:` line picks passes
`checkout-only: 'true'`. Either way the action merges the pull requests named in
the repository under test into its checkout, so a step that reads the checkout,
an install from its lockfile among them, comes after it. A job that reads the
EARL report a run wrote reads the action's `report` output, never a path it
assumes.

## The workflow an adapter and an engine both run

`check.yml`, the main workflow:

```yaml
on:
  push:
    branches: [main]
  pull_request:
    types: [opened, synchronize, reopened]
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
```

`ready.yml`, the merge gate:

```yaml
name: ready-to-merge

on:
  pull_request:
    types: [opened, synchronize, reopened, edited]

jobs:
  ready-to-merge:
    name: ready-to-merge
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    concurrency:
      group: ready-${{ github.ref }}
      cancel-in-progress: true
    steps:
      - uses: jayostis/cascade-bridge-spec/.github/actions/start@main
        with:
          check: ready-to-merge

  rerun-when-edited:
    if: github.event.action == 'edited'
    runs-on: ubuntu-latest
    timeout-minutes: 15
    permissions:
      actions: write
      pull-requests: read
    steps:
      - uses: jayostis/cascade-bridge-spec/.github/actions/rerun-when-edited@main
        with:
          workflows: check.yml
```

Make `compatibility` and `ready-to-merge` required status checks, and keep
whatever you have named them: a renamed job leaves every merge waiting on a
check that never reports. An edit to a description starts only `ready.yml`,
because only a changed `Depends-On:` line or base changes what `compatibility`
reads: then `rerun-when-edited` re-runs the latest run of each workflow it names
on the pull request's head, in full, cancelling it first where it is still
running. Any other edit re-runs nothing. `pull-requests: write` is what the
action posts the table with, in a step of its own: the checks are the version
the run picked — a named pull request's own code, where one is named — and are
given the token to read GitHub's API with, and post nothing. `actions: write` is
what `rerun-when-edited` re-runs with, in a job of its own that checks nothing
out and runs nothing the run picked. The merge gate cancels its own run in
flight, which read the description at its start. On a pull request from a fork
the token is read-only whatever the workflow asks for, and the run says so rather than failing.
