# Compatibility between engines and adapters

A repository may commit a `compatibility.json` at its root naming the adapters
(in an engine) or engines (in an adapter) it must pass with. **Every entry that
does not hold blocks the merge.**

Its keys are [`vocab/compatibility.context.jsonld`](vocab/compatibility.context.jsonld),
each a `bridge:` term in [`vocab/bridge.ttl`](vocab/bridge.ttl), checked by the
compatibility shapes in [`shapes/bridge.shapes.ttl`](shapes/bridge.shapes.ttl).
An engine's file:

```json
{
  "@context": "https://ns.cascadeprotocol.org/bridge/v1-draft/compatibility.jsonld",
  "setup": ["npm", "ci"],
  "command": ["node", "packages/bridge-cli/src/cli.ts"],
  "mustPassWith": ["https://github.com/jayostis/cascade-bridge-adapter-clinvar"]
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
- otherwise the branch named like the branch the pull request under test targets;
- otherwise the default branch.

A local run uses every sibling checkout as it is on disk, uncommitted edits
included.

A pull request merges only once every pull request it names has merged.

**A `Depends-On:` line goes one way.** A cycle fails, as in Zuul without
[circular dependencies](https://zuul-ci.org/docs/zuul/latest/config/queue.html).
A change an engine and an adapter must both follow goes in backward-compatible
steps, each leaving every default branch green.

Where GitHub Actions cannot reproduce Zuul:

- Editing a named pull request retests nothing; rerun the workflow.
- There is no gate queue, so a pass is as fresh as its last run.
- A repository's state is not frozen across a run's jobs.

## The tooling

[`scripts/compatibility.py`](scripts/compatibility.py); its docstring is the
usage. A repository's CI calls only `.github/actions/start@start-v2`
([`adapter/validation.md`](adapter/validation.md) shows the workflow). A pull
request here that changes the tooling is tried first from a no-op engine or
adapter pull request naming it on a `Depends-On:` line, as a change to Zuul's
shared jobs is.
