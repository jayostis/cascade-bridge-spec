from types import SimpleNamespace

import _crate


class TestCheckingAnAdapterPackageAgainstTheProfile:
    """Checking an adapter package against the profile · rocrate-validator, adapter/profile/must/

    An adapter package conforms when `rocrate-validator` passes it against RO-Crate 1.2 and this profile. Each `.ttl` or
    `.py` file under `adapter/profile/must/` is one requirement, and a requirement that could not be checked fails the
    package and says why.
    """

    class TestGivenAPackageNamedByAFileURI:
        """given a package named by a `file:` URI"""

        def test_reads_the_package_from_the_folder_the_uri_names(self, crate):
            """reads the package from the folder the URI names"""
            context = SimpleNamespace(settings=SimpleNamespace(rocrate_uri=crate.adapter.as_uri()))
            assert _crate.from_context(context).adapter == crate.adapter.resolve()
