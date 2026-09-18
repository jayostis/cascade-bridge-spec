# cascade-bridge-spec

The **Cascade Bridge Specification**: the contract every Cascade Bridge Adapter
(a data package for one source format) and every Cascade Bridge (an
implementation that runs adapters, one per language) follows.

**DRAFT: no compatibility is promised before a numbered v1.** Every namespace is
`v1-draft`, and the profile IRI does not dereference yet.

Normative: [`vocab/`](vocab/), [`shapes/`](shapes/),
[`adapter/profile/`](adapter/profile/), [`engine/sparql.md`](engine/sparql.md),
[`engine/command.md`](engine/command.md), [`pinning.md`](pinning.md) and
[`compatibility.md`](compatibility.md).

| you are building | start at |
|---|---|
| an adapter | [`adapter/`](adapter/) |
| an engine | [`engine/`](engine/) |

Apache-2.0.
