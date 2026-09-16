# Compatibility between engines and adapters

A repository may commit a `compatibility.json` at its root saying "also test me
against this adapter" (an engine) or "against this engine" (an adapter). **Every
entry is an assertion, and a failed assertion blocks the merge.** Why pins work
this way is [`pinning.md`](pinning.md).

## The file

JSON that is also JSON-LD, through
[`vocab/compatibility.context.jsonld`](vocab/compatibility.context.jsonld), the
list of keys there are. What each key means is its `bridge:` term's
`rdfs:comment` in [`vocab/bridge.ttl`](vocab/bridge.ttl); what is checked is the
shapes at the end of [`shapes/bridge.shapes.ttl`](shapes/bridge.shapes.ttl) and
`validate` below.

```json
{
  "@context": "https://ns.cascadeprotocol.org/bridge/v1-draft/compatibility.jsonld",
  "specification": {
    "codeRepository": "https://github.com/jayostis/cascade-bridge-spec",
    "commit": "7a614179c4856a3f6e1a4b5a6c90a183b0c7c99a"
  },
  "setup": ["npm", "ci"],
  "command": ["node", "packages/bridge-cli/src/cli.ts"],
  "testedWith": [
    { "codeRepository": "https://github.com/jayostis/cascade-bridge-adapter-clinvar", "branch": "main" }
  ]
}
```

An adapter's file has only `testedWith`: its spec pin stays in its crate, where a
host loading the adapter reads it. A directory holding `ro-crate-metadata.json` is
an adapter.

**A commit or tag pin is reproducible**: green on a pull request stays green once
merged. **A default-branch pin** means "keep me current, and block me when the
other side breaks me", and the other side merging can turn this one red with no
change of its own.

## Changing an entry

- **Opt out** by deleting the entry or re-pinning it. There is no "expected to
  fail" entry; the pull request carries the reason.
- **Add a pairing after both sides have merged**, so a new assertion cannot
  deadlock two open pull requests.
- **A breaking change resolves in the open**: the engine removes or re-pins the
  adapter's entry and merges, the adapter follows, the engine re-adds the entry.

## The tooling

[`scripts/compatibility.py`](scripts/compatibility.py): its docstring lists the
subcommands. A repository's CI calls only the starter,
`.github/actions/start@start-v1`, a tag that never moves ([`adapter/validation.md`](adapter/validation.md) shows the
workflow). The starter checks this repository out at the caller's spec pin and
hands over to the actions beside it, so the spec pin is written in one place.

Every counterpart is checked out beside the repository under test, in a
directory named as its repository. A run records the commit each pin resolved
to; a result from a sibling's uncommitted edits is feedback, never evidence.
