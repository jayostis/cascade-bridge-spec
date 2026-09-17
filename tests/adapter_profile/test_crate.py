from types import SimpleNamespace

import _crate


def test_reads_the_package_from_a_file_uri_with_no_path_attribute(package):
    context = SimpleNamespace(settings=SimpleNamespace(rocrate_uri=package.path.as_uri()))
    assert _crate.from_context(context).adapter == package.path.resolve()
