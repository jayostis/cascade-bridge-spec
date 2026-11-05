# Validating an adapter package

An adapter package conforms when `rocrate-validator` passes it against RO-Crate
1.2 and [`profile/`](profile/). Each requirement is a file in
[`profile/must/`](profile/must/), and what it reports is its test in
[`../tests/adapter_profile/`](../tests/adapter_profile/).

```bash
python3 -m pip install --group <this repository>/pyproject.toml:validators
rocrate-validator validate <adapter> \
  --extra-profiles-path <this repository>/adapter \
  --profile-identifier cascade-bridge-adapter --no-paging --verbose
```

Once a `bridge:carriedAs` in the adapter's source accounting names a term, the Cascade vocabulary repository its
`bridge:cascadeVocabularyRepository` names must be checked out beside the adapter, in a folder named as the
repository is. Without it the run fails with one "not checked out" issue and checks no term.

Nothing an adapter names is fetched. A media type the profile does not allow is
a pull request here, not one invented in an adapter.

In CI this runs from the workflow in
[`../compatibility.md`](../compatibility.md).
