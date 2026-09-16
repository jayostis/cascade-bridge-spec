# shapes — Agent Context

`bridge.shapes.ttl` is what an adapter's crate (`ro-crate-metadata.json`, parsed
as JSON-LD) and its test manifest are validated against **as one graph**, each
with its own file location as base, so the manifest's `<../>` is the crate's root
entity. The cross-file constraints — that a test's envelope is one the adapter
lists, and that the manifest and adapter point at each other — are
`sh:sparql`, so pySHACL must run with `advanced=True`.

Adding a media type to the allowed `encodingFormat` set is a change to the "no
code" guarantee the file header describes, not housekeeping.

- Shapes are valid SHACL:
  `python3 -m pyshacl --metashacl --shacl shapes/bridge.shapes.ttl shapes/bridge.shapes.ttl`
- **A changed shape is run against a real adapter checkout by hand**, and the
  commit says which adapter and at which commit. Not in CI: a job that cloned an
  adapter would go red for somebody else's missing property, and would grow a job
  per adapter forever (`../pinning.md`).
- **A shape meant to reject something is verified by seeing it fail** — break a
  copy, watch it go red, restore it. A constraint nobody saw fail is a
  constraint nobody knows fires. Add the case to `selftest-lint.py`, which runs
  its cases concurrently and takes a name to run one; keep it that way, because
  a suite too slow to run on every edit stops being run at all
  (`../scripts/CLAUDE.md`).
- **Every constraint carries an `sh:message` that names what was wanted**, and
  the `sh:in` sets spell their members out. `../adapter/validation.md` and
  `../compatibility.md` send the reader here rather than copying, so a failing
  run's own output is the whole answer.
- The `compatibility.json` shapes target only compatibility terms. A target that
  reached a crate — `bridge:specPin`, say — would put an engine's rules on every
  adapter the lint validates.
