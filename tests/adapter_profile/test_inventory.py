import inventory


def test_reports_nothing_when_every_tracked_file_is_described_or_allowlisted(crate):
    assert not list(inventory.unaccounted(crate))


def test_reports_a_tracked_file_the_crate_describes_nowhere(package):
    package.write("fixtures/in/undescribed.xml", "<ExampleRecord/>")
    found = "\n".join(inventory.unaccounted(package.crate))
    assert "undescribed.xml" in found
    assert "no crate entity with a declared encodingFormat" in found
    assert "not one of README.md, LICENSE, CHANGELOG.md, CLAUDE.md, ro-crate-metadata.json or a dotfile" in found


def test_allowlists_the_repository_documents_and_dotfiles(package):
    package.write("README.md", "# nothing the crate describes")
    package.write(".editorconfig", "root = true")
    assert not list(inventory.unaccounted(package.crate))


def test_reports_a_package_that_is_not_a_git_checkout(loose):
    assert "is not a git checkout" in "\n".join(inventory.unaccounted(loose.crate))
