# scripts — Agent Context

Published machinery: it runs in every adapter's and engine's CI from a checkout
of the version the run picks.

- **Nothing here learns an adapter's or an engine's name.** A tool takes a directory.
- **Nothing mutates a tracked file.** Mutation happens on a copy.
- **A rule lands with a test case that asserts it**, in the same commit.
- **A suite is fast enough to run on every edit.**
- **A docstring is usage, not a description of the code.**

```bash
python3 -m pip install --group dev
python3 -m pytest tests/compatibility
```
