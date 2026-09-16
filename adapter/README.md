# Building an adapter

An adapter is a package of data for one XML source format, with no code in it.
Read, in order:

1. [`ro-crate-metadata.md`](ro-crate-metadata.md): the crate, which is the package's manifest.
2. [`../engine/sparql.md`](../engine/sparql.md): what your queries run over.
3. [`fixtures/README.md`](fixtures/README.md): fixtures and their provenance.
4. [`fixtures/manifest.md`](fixtures/manifest.md): the test manifest.
5. [`validation.md`](validation.md): running the checks.

What each term means is its `rdfs:comment` in
[`../vocab/bridge.ttl`](../vocab/bridge.ttl). What is checked is
[`profile/`](profile/) and [`../shapes/bridge.shapes.ttl`](../shapes/bridge.shapes.ttl),
and a failing run's messages say what was wanted.
