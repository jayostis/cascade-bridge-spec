# scripts — Agent Context

Machinery, not contract: `../adapter/validation.md` is the contract and
`validate-adapter.py` implements it. But it is the *published* machinery, run in
every adapter's CI from a checkout at that adapter's own spec pin
(`../compatibility.md`), so a change here is felt by an adapter when it moves its
pin and not before. That is the whole reason the pin exists.

`selftest-lint.py` is the answer to "what would the lint report if the thing it
claims to check were wrong?" It mutates a copy of `../fixtures/synthetic-adapter`
in a temporary directory and asserts the lint says so, in the words
`../adapter/validation.md` fixes. A check that quietly does nothing and reports a
pass is invisible from a green run.

`compatibility.py` implements `../compatibility.md`, and is published the same
way, through the actions the starter hands over to. `selftest-compatibility.py`
asks it the same question, against throwaway git repositories it makes in a
temporary directory and names by `file://` URLs: no network, and no real
adapter or engine.

- **Nothing here may learn an adapter's or an engine's name.** The tools take a
  directory and read the files in it; `../fixtures/README.md` says why their
  test subjects are synthetic.
- **Nothing mutates a tracked file.** Mutation happens on a copy, outside the
  repository.
- **A check that is specified but not built says so in the output.** A package
  that passed three checks must not read as though it passed every check.
- A new check lands with `../adapter/validation.md` and a `selftest-lint.py` case in
  the same commit; a new rule in `compatibility.py` with `../compatibility.md` and
  a `selftest-compatibility.py` case.
- **The selftests set their own temporary directory for each run**, so a record
  or a worktree a tool makes goes with the case, and never into a developer's
  directory.
- **A selftest suite is fast enough to run on every edit**, because a suite
  people stop running is worth nothing however many cases it has. Measure
  before optimising it: here one case costs about 16 seconds and effectively all
  of that is `rocrate-validator` loading RO-Crate's profiles before it looks at
  the crate. So cases run concurrently rather than one after another, and a case
  is selectable by name, so that changing four costs four and not all of them.
  A filtered run says how many it skipped: a filtered PASS is not the suite
  passing.

```bash
python3 -m pip install pyshacl rdflib roc-validator lxml
python3 scripts/validate-adapter.py <path to an adapter checkout>
python3 scripts/selftest-lint.py
python3 scripts/compatibility.py validate <path to a repository>
python3 scripts/selftest-compatibility.py
```

The adapter run stays out of CI on purpose; `../pinning.md` says why.
