# scripts — Agent Context

Machinery, not contract: `../docs/validation.md` is the contract and
`validate-adapter.py` implements it. But it is the *published* machinery — an
adapter's CI calls it through `../.github/actions/validate-adapter` at a tag — so
a change here is felt by every adapter at its next tag, and by none of them
before. That is the whole reason the pin exists.

`selftest-lint.py` is the answer to "what would the lint report if the thing it
claims to check were wrong?" It mutates a copy of `../fixtures/synthetic-adapter`
in a temporary directory and asserts the lint says so, in the words
`../docs/validation.md` fixes. A check that quietly does nothing and reports a
pass is invisible from a green run.

- **Nothing here may learn an adapter's name.** The lint takes a directory. A
  path, repository name or fixture id specific to one adapter is the bug this
  repository was corrected for at 0.2.0. `../fixtures/README.md` says why the
  test subject is synthetic.
- **Nothing mutates a tracked file.** Mutation happens on a copy, outside the
  repository.
- **A check that is specified but not built says so in the output.** A package
  that passed three checks must not read as though it passed six.
- A new check lands with `../docs/validation.md` and a `selftest-lint.py` case in
  the same commit.

```bash
python3 -m pip install pyshacl rdflib roc-validator
python3 scripts/validate-adapter.py <path to an adapter checkout>
python3 scripts/selftest-lint.py
```

The adapter run stays out of CI on purpose; `../CLAUDE.md` says why.
