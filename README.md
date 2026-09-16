# cascade-bridge-spec

The **Cascade Bridge Specification**: the contract every Cascade Bridge Adapter
and every Cascade Bridge implementation follows.

| term | what it is |
|---|---|
| **Cascade Bridge Specification** | this repository |
| **Cascade Bridge for `<language>`** | an implementation, once per language |
| **Cascade Bridge Adapter** | a data package for one source format |

The Bridge depends on the Cascade runtime and the runtime never depends on the
Bridge: format knowledge leaves the runtime and becomes data.

## Status: DRAFT

**No compatibility is promised before a numbered v1.** Every namespace is
`v1-draft`, and the profile IRI does not dereference yet. v1-draft specifies XML
source formats and the `sparql-1.1` profile, and nothing else.

Normative: [`vocab/`](vocab/), [`shapes/`](shapes/),
[`adapter/profile/`](adapter/profile/), [`engine/sparql.md`](engine/sparql.md),
[`engine/command.md`](engine/command.md), [`pinning.md`](pinning.md) and
[`compatibility.md`](compatibility.md). Where prose and the Turtle disagree, the
Turtle is right.

Not settled, and not answerable from this repository:

- **what Core contains**, beneath the profiles an adapter requires;
- **the canonical findings model** ([`adapter/fixtures/README.md`](adapter/fixtures/README.md));
- **router precedence** when two adapters' detect queries match one document;
- **the export direction**: import only is specified;
- **Cascade's vocabularies**, which live in the `spec` repository.

## Start here

| you are building | start at |
|---|---|
| an adapter | [`adapter/`](adapter/) |
| an engine | [`engine/`](engine/) |

Both pin a revision of this repository: [`pinning.md`](pinning.md).

## Licence

Apache-2.0.
