# shapes — Agent Context

What `bridge.shapes.ttl` covers is its header. These rules hold for it and for
the shapes in `../adapter/profile/must/`.

- Shapes are valid SHACL: the `spec` job in `../.github/workflows/validate.yml`.
- **A changed shape is run against a real adapter checkout by hand**, and the
  commit says which adapter and at which commit. Not in CI: a job that cloned an
  adapter would go red for somebody else's missing property, and would grow a job
  per adapter forever (`../pinning.md`).
- **A shape meant to reject something is verified by seeing it fail** — break a
  copy, watch it go red, restore it. A constraint nobody saw fail is a
  constraint nobody knows fires. It gets a test that sees it fail, and that
  test stays fast enough to run on every edit (`../scripts/CLAUDE.md`).
- **Every constraint carries an `sh:message` that names what was wanted**, and
  the `sh:in` sets spell their members out. `../adapter/validation.md` and
  `../compatibility.md` send the reader here rather than copying, so a failing
  run's own output is the whole answer.
- The `compatibility.json` shapes target only compatibility terms. A target that
  reached a crate — `bridge:specPin`, say — would put an engine's rules on every
  adapter the lint validates.
