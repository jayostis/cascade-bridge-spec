# shapes — Agent Context

`bridge.shapes.ttl` is what an adapter's crate (`ro-crate-metadata.json`, parsed
as JSON-LD) and its test manifest are validated against **as one graph**, each
with its own file location as base, so the manifest's `<../>` is the crate's root
entity. The cross-file constraints — that a test's envelope is one the adapter
lists, and that the manifest and adapter point at each other — are
`sh:sparql`, so pySHACL must run with `advanced=True`.

The allowed `encodingFormat` set lives here. It is what keeps a file that
executes out of a package that claims to be data, so adding a media type to it is
a change to the "no code" guarantee, not housekeeping.

- Shapes are valid SHACL:
  `python3 -m pyshacl --metashacl --shacl shapes/bridge.shapes.ttl shapes/bridge.shapes.ttl`
- **A changed shape is run against a real adapter checkout by hand**, and the
  commit says which adapter and at which commit. Not in CI: a job that cloned an
  adapter would go red for somebody else's missing property, and would grow a job
  per adapter forever (`../pinning.md`).
- **A shape meant to reject something is verified by mutation** — break the
  adapter's copy, see it go red, restore it, see it go green. A constraint nobody
  saw fail is a constraint nobody knows fires.
- What each shape checks must match `../adapter/validation.md` exactly.
