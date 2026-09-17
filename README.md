# cascade-bridge-spec

The **Cascade Bridge Specification**: the contract every Cascade Bridge Adapter
(a data package for one source format) and every Cascade Bridge (an
implementation that runs adapters, one per language) follows.

**DRAFT: no compatibility is promised before a numbered v1.** Every namespace is
`v1-draft`, and the profile IRI does not dereference yet. v1-draft specifies XML
source formats and the `sparql-1.1` profile.

Normative: [`vocab/`](vocab/), [`shapes/`](shapes/),
[`adapter/profile/`](adapter/profile/), [`engine/sparql.md`](engine/sparql.md),
[`engine/command.md`](engine/command.md), [`pinning.md`](pinning.md) and
[`compatibility.md`](compatibility.md).

Nothing here pins an adapter or an engine, and nothing pins this repository. A
run picks which version of each repository it uses when it starts, following
[OpenStack's Zuul model](https://zuul-ci.org/docs/zuul/latest/gating.html) as
closely as GitHub Actions allows; [`compatibility.md`](compatibility.md) states
it, and names every departure from it and what someone must do by hand instead.

Not settled: what Core contains, the canonical findings model
([`adapter/fixtures/README.md`](adapter/fixtures/README.md)), router precedence
when two adapters' detect queries match one document, and the export direction.

| you are building | start at |
|---|---|
| an adapter | [`adapter/`](adapter/) |
| an engine | [`engine/`](engine/) |

Apache-2.0.
