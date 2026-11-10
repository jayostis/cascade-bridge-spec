import inventory


class TestFilesAPackageTracks:
    """Files a package tracks · adapter/profile/must/inventory.py

    Every file git tracks in an adapter's repository is described by the crate, or is one of the files that describe the
    repository itself.
    """

    class TestGivenAPackageWhoseTrackedFilesAreAllAccountedFor:
        def test_reports_nothing_when_every_tracked_file_is_described_or_allowlisted(self, crate):
            assert not list(inventory.unaccounted(crate))

        def test_allowlists_the_repositorys_documents_and_dotfiles(self, tracked_package):
            """allowlists the repository's documents and dotfiles"""
            tracked_package.write("README.md", "# nothing the crate describes")
            tracked_package.write(".editorconfig", "root = true")
            assert not list(inventory.unaccounted(tracked_package.crate))

        def test_allowlists_an_adapters_compatibility_json(self, tracked_package):
            """allowlists an adapter's `compatibility.json`"""
            tracked_package.write("compatibility.json", '{"mustPassWith": []}')
            assert not list(inventory.unaccounted(tracked_package.crate))

    class TestGivenAPackageAtFault:
        def test_reports_a_tracked_file_the_crate_describes_nowhere(self, tracked_package):
            tracked_package.write("fixtures/in/undescribed.xml", "<ExampleRecord/>")
            found = "\n".join(inventory.unaccounted(tracked_package.crate))
            assert "undescribed.xml" in found
            assert "no crate entity with a declared encodingFormat" in found
            assert (
                "not one of README.md, LICENSE, CHANGELOG.md, CLAUDE.md, ro-crate-metadata.json, compatibility.json or a dotfile"
                in found
            )

        def test_reports_a_package_that_is_not_a_git_checkout(self, package):
            assert "is not a git checkout" in "\n".join(inventory.unaccounted(package.crate))
