from types import SimpleNamespace

import _crate


def test_reads_the_package_from_a_file_uri_with_no_path_attribute(crate):
    context = SimpleNamespace(settings=SimpleNamespace(rocrate_uri=crate.adapter.as_uri()))
    assert _crate.from_context(context).adapter == crate.adapter.resolve()
