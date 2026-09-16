"""The adapter lint, one module per check.

adapter/validation.md is the contract; this implements it. Each module under
`checks/` exposes `run(...)` returning a `Result` and prints nothing, so a
check's verdict can be asserted in a test that takes microseconds rather than
by running the whole lint and reading its output. `report.py` is the only
module that knows what any of it looks like on a terminal.
"""
