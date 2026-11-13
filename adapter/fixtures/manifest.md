# The test manifest

An adapter declares its cases as a W3C test manifest (`mf:`) in Turtle, named by
the crate's `bridge:testManifest`, and a Bridge executes it
([`../../engine/executing.md`](../../engine/executing.md)). What it carries is
`<#Manifest>` in [`../../shapes/bridge.shapes.ttl`](../../shapes/bridge.shapes.ttl);
how each entry type is judged is that type's `rdfs:comment` in
[`../../vocab/bridge.ttl`](../../vocab/bridge.ttl).
[`../../fixtures/synthetic-adapter/fixtures/manifest.ttl`](../../fixtures/synthetic-adapter/fixtures/manifest.ttl)
is one that passes.

A test case may name its concern with `bridge:concern`; the profile module that reads the tag is
[`../profile/must/shapes.py`](../profile/must/shapes.py), and the tag is described in
[`../README.md`](../README.md#saying-what-a-mapping-is-about).

Relative IRIs resolve against the manifest's own location, so `<../>` is the
crate's root entity.
