# shapes — Agent Context

Holds for `bridge.shapes.ttl` and the shapes in `../adapter/profile/must/`.

- **A shape meant to reject something has a test that sees it reject it.**
- **Every constraint's `sh:message` says what was wanted**, and an `sh:in` set
  spells its members out: a failing run's output is the whole answer.
- **No `sh:description` or `#` comment restating a constraint.**
- **A changed shape is run by hand against a real adapter checkout**, and the
  commit message names which, at which commit. Never in CI.
- The `compatibility.json` shapes target only compatibility terms.
