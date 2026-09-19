# Fixtures

Every file an adapter ships and every dataset it references is an entity in the
crate; [`../profile/must/`](../profile/must/) checks what each carries.

- **`sha256`** is recomputed over the committed bytes. A publisher's own digest
  is recorded beside it under its own term, never merged into it.
- **A digested file is never edited**: replace it from its source and restate
  its digest and size in the same commit. Keep line-ending normalisation and
  save-time trimming off it in `.gitattributes` and `.editorconfig`.
- **What is not known about a file's provenance is recorded as not known.**
- **A dataset too large to commit is referenced** by a dated release file, never
  a "latest" pointer.

```
fixtures/in/<mf:name>.<ext>       the source document
fixtures/expected/<mf:name>.ttl   the graph it must produce
fixtures/findings/<mf:name>.ttl   the findings it must produce
```

[`../../fixtures/synthetic-adapter/`](../../fixtures/synthetic-adapter/) is a
package laid out this way.
