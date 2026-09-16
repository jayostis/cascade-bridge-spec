# scripts — Agent Context

Machinery, and *published* machinery: it runs in every adapter's CI from a
checkout at that adapter's own spec pin (`../compatibility.md`), so a change here
is felt by an adapter when it moves its pin and not before. That is the whole
reason the pin exists.

What is where is each file's own docstring. The rules that are not:

- **Nothing here may learn an adapter's or an engine's name.** The tools take a
  directory and read the files in it; `../fixtures/README.md` says why their
  test subjects are synthetic.
- **Nothing mutates a tracked file.** Mutation happens on a copy, outside the
  repository.
- A new rule in `compatibility.py` lands with `../compatibility.md` and a
  `selftest-compatibility.py` case, in the same commit.
- **The selftests set their own temporary directory for each run**, so a record
  or a worktree a tool makes goes with the case, and never into a developer's
  directory.
- **A suite is fast enough to run on every edit**, because a suite people stop
  running is worth nothing however many cases it has.

```bash
python3 -m pip install --group dev
python3 scripts/compatibility.py validate <path to a repository>
python3 scripts/selftest-compatibility.py
```
