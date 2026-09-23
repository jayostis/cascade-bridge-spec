# Fixtures

Everything here is invented: this repository must not know that any real adapter
or engine exists ([`../pinning.md`](../pinning.md)).

An expected findings file is compared as a graph, as `bridge:comparison` says,
and a Bridge is not asked to write the same bytes twice: a blank node's label is
its own, and the order a mapping's solutions arrive in may differ between one
execution of a query and the next. So an adapter's digest of such a file records
what was committed, a regeneration's diff carries no meaning, and what an oracle
asserts is the graph it holds.
