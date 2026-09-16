# scripts — Agent Context

Machinery, not contract: `../adapter/validation.md` is the contract. It is
implemented as an RO-Crate profile, `profiles/cascade-bridge-adapter`, whose
requirements rocrate-validator runs beside RO-Crate 1.2's own; `bridgelint/` is
what those requirements call, one module per requirement, each returning a
`Result` and printing nothing; `validate-adapter.py` runs the profile and prints
what it found. A requirement is a dozen lines because the deciding is in
`bridgelint/checks/` where a test can reach it.

But it is the *published* machinery, run in every adapter's CI from a checkout
at that adapter's own spec pin (`../compatibility.md`), so a change here is felt
by an adapter when it moves its pin and not before. That is the whole reason the
pin exists.

`unittest-lint.py` asserts what each requirement decides, calling it directly:
no subprocess, no validator, seconds. `selftest-lint.py` is what only a whole
run shows — that the profile loads, that this specification's requirements run
beside the inherited ones, and that the exit status is right. A check that
quietly does nothing and reports a pass is invisible from a green run.

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
- A new requirement lands as a module in `bridgelint/checks/`, a dozen-line file
  in `profiles/cascade-bridge-adapter/must/` that calls it, `../adapter/validation.md`
  and a `unittest-lint.py` test, in the same commit; a new rule in
  `compatibility.py` with `../compatibility.md` and a `selftest-compatibility.py`
  case.
- **The selftests set their own temporary directory for each run**, so a record
  or a worktree a tool makes goes with the case, and never into a developer's
  directory.
- **A suite is fast enough to run on every edit**, because a suite people stop
  running is worth nothing however many cases it has. Measure before optimising
  it: a whole-run case costs about 10 seconds and effectively all of that is
  rocrate-validator, which is why what can be asserted about a decision is
  asserted against the decision. Cases run concurrently, and a case is
  selectable by name so that changing four costs four. A filtered run says how
  many it skipped: a filtered PASS is not the suite passing.

```bash
python3 -m pip install pyshacl rdflib roc-validator lxml
python3 scripts/validate-adapter.py <path to an adapter checkout>
python3 scripts/unittest-lint.py
python3 scripts/selftest-lint.py
python3 scripts/compatibility.py validate <path to a repository>
python3 scripts/selftest-compatibility.py
```

The adapter run stays out of CI on purpose; `../pinning.md` says why.
