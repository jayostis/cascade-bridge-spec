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
  "specPin": {
    "codeRepository": "https://github.com/jayostis/cascade-bridge-spec",
    "commit": "7a614179c4856a3f6e1a4b5a6c90a183b0c7c99a"
  },
  "setup": ["npm", "ci"],
  "command": ["node", "packages/bridge-cli/src/cli.ts"],
  "mustPassWith": [
    { "codeRepository": "https://github.com/jayostis/cascade-bridge-adapter-clinvar", "branch": "main" }
  ]
}
```

An adapter's file has only `mustPassWith`; its spec pin is `bridge:specPin` in its crate.

A commit or tag pin is reproducible. A default-branch pin can turn red when the
other side merges, with no change of its own.

## Changing an entry

- **Opt out** by deleting the entry or re-pinning it. There is no "expected to
  fail" entry.
- **Add a pairing after both sides have merged.**
- **A breaking change**: the engine removes or re-pins the adapter's entry and
  merges, the adapter follows, the engine re-adds the entry.

## The tooling

[`scripts/compatibility.py`](scripts/compatibility.py); its docstring is the
usage. A repository's CI calls only `.github/actions/start@start-v1`
([`adapter/validation.md`](adapter/validation.md) shows the workflow).
