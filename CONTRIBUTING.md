# Contributing to cascade-bridge-spec

Thank you for helping. This repository is the Cascade Bridge Specification: the contract every Cascade Bridge Adapter
and every Bridge follows. It is a draft; no compatibility is promised before a numbered v1.
[`CLAUDE.md`](CLAUDE.md) holds the rules a change here follows, and [`README.md`](README.md) says where to start.

Please follow the organisation's code of conduct and security policy. Report a security problem privately, as that
policy says, never in a public issue.

## Set up

You need Python 3.12 and git.

```sh
git clone git@github.com:<you>/cascade-bridge-spec.git
cd cascade-bridge-spec
python3 -m pip install --group dev
```

The `dev` group in [`pyproject.toml`](pyproject.toml) pins pytest, ruff and the validators. Some specification tests
read [cascade-vocabulary](https://github.com/jayostis/cascade-vocabulary) as a sibling folder: clone it beside this
repository, or run `python3 scripts/place_vocabulary.py ../cascade-vocabulary`, which is what CI does.

## Run the checks

These are the commands CI runs.

```sh
python3 -m ruff check .
python3 -m ruff format --check .
python3 -m pytest
rocrate-validator validate adapter/profile/ --profile-identifier ro-crate-1.2 --no-paging
```

`pytest` takes its options from `pyproject.toml` and runs in parallel and in random order. A run prints its seed; pass
it back with `-p randomly --randomly-seed=N`. CI splits the suite into three slices only to be quicker, so one
`python3 -m pytest` covers them all. While you work, run the directory you touched, for example
`python3 -m pytest tests/compatibility`.

Ruff does not read Markdown, so a change to prose alone has nothing for it to fail on.

## What a pull request must pass

All of these must be green before a merge.

- **`ruff`**: lint and format, as above.
- **`pytest`** slices, and **the tests read as a specification**: every top-level test class is a heading listed in
  [`tests/spec.json`](tests/spec.json), and its situations name code or begin with "when", "given" or "with". A new or
  renamed test class needs its entry there by hand.
- **The adapter profile's own crate** validates against RO-Crate 1.2.
- **The published GitHub Actions** run on the synthetic adapters.
- **`ready-to-merge`**: holds a pull request until every pull request it depends on can merge (see below).

## What a change here means

Writing less is the default. [`CLAUDE.md`](CLAUDE.md) explains why a comment, a docstring or an `rdfs:comment` that
restates a name is a defect, and why deleting prose is always welcome. A behaviour this repository cannot run, a
Bridge's, is specified by vectors under `fixtures/`, and by the shortest normative sentence only where a vector cannot
say it.

A change to `vocab/`, `shapes/`, `adapter/profile/`, `engine/sparql.md`, `engine/command.md` or `compatibility.md`
changes what every adapter and Bridge must do. A change to `bench/` changes what every benchmark harness must write.
Either way, the commit message says why.

## Commits and pull requests

Use conventional commits: `feat(spec): ...`, `docs: ...`, `fix(shapes): ...`. Do not put a closing keyword (`closes`,
`fixes`, `resolves`) before an issue the pull request does not finish: GitHub closes it whatever the rest of the
sentence says.

## A change that spans two repositories

Nothing pins this specification, an engine, an adapter, a runtime or a vocabulary to a commit of another. Each is
tested against the others' default branches, and a change that must land in several is a set of pull requests that name
each other. Each names the ones it needs in its description, on a line of its own, with the full URL:

```
Depends-On: https://github.com/jayostis/cascade-bridge-rs/pull/123
```

The `compatibility` check of each repository then runs the named pull requests together, and `ready-to-merge` holds each
until the others can merge. A person merges the set one after another, and the default branch is red between the first
merge and the last. A breaking change does not get a second accepted form to keep the default branch green.

What GitHub Actions cannot reproduce is done by hand:

- A change to a named pull request retests nothing. Re-run the dependent pull request's workflow with `gh run rerun`.
- There is no merge queue. Re-run `compatibility` and `ready-to-merge` just before you merge.
- A pull request from a fork has a read-only token, so editing its description re-runs nothing. Run `gh run rerun`.

[`compatibility.md`](compatibility.md) has the whole set of rules, and says where this departs from the OpenStack Zuul
model it follows. Review a pull request here as code that will run in every repository whose pull request names it.

## Licence

Apache-2.0.
