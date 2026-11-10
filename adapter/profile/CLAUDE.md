A requirement lands with its tests in `../../tests/adapter_profile/`, in the same
commit, and a test is a leaf under a situation under a capability, which together are
the sentence it asserts (a docstring is the leaf's title; see
`../../tests/CLAUDE.md`): `python3 -m pip install --group dev`, then
`python3 -m pytest`. `profile.ttl` is the descriptor; every other `.ttl` or `.py`
under this directory is a requirement `rocrate-validator` discovers and runs, and a
module a check imports is named with a leading underscore, which is what keeps it
out.
