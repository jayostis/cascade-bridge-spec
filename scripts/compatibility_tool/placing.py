from compatibility_tool import git, picking
from compatibility_tool.console import Stop
from compatibility_tool.github import repository_name, repository_path, url_on_this_server
from compatibility_tool.record import MergedHead, Role, Row


def sibling(directory, url):
    path = directory.parent / repository_name(url)
    if not (path / ".git").exists():
        raise Stop(f"{url} has no clone beside {directory.name}; clone it with: git clone {url} {path}")
    return path


def toplevel(directory, fallback):
    return git.toplevel(directory) or fallback


def under_test_is(event, merged=()):
    if not event.number:
        return f"{event.branch}, the branch this run is on"
    tested = f"pull request #{event.number} merged into {event.branch}"
    return f"{tested}, and {picking.numbered(merged)} merged into it" if merged else tested


def partners_merged(directory, event, reached):
    """Each pull request named in the repository under test, merged into its checkout so the set is tested as it
    will land; in the order of their numbers, so each member of a cycle merges the others alike."""
    entries = picking.partners(reached, event)
    if not entries:
        return []
    elsewhere = [entry for entry in entries if entry.base != event.branch]
    if elsewhere:
        raise Stop(
            "; ".join(
                f"{entry.named.label} targets {entry.base}, and the pull request under test {event.branch}"
                for entry in elsewhere
            )
            + ": they land on different branches, so the run cannot test them as one"
        )
    url = url_on_this_server(event.repository)
    git.deepen(url, directory)
    for at, entry in enumerate(entries):
        head = git.fetch(url, f"refs/pull/{entry.named.number}/head", directory)
        if git.merge(directory, head, entry.named.label):
            raise Stop(
                f"{entry.named.label} does not merge cleanly into {under_test_is(event, entries[:at])}: "
                "bring one up to date with the other, or fold them into one pull request"
            )
    return entries


def working_tree_is(path, role):
    branch = git.current_branch(path) or "a detached HEAD"
    where = "its working tree" if role is Role.UNDER_TEST else "the sibling's working tree"
    return f"{where}, on {branch}"


def on_disk(name, url, path, role, how=None, merged=False):
    return Row(
        name=name,
        repository=url,
        commit=git.local_commit(path, "HEAD"),
        how=how or working_tree_is(path, role),
        role=role,
        uncommitted_edits=git.has_uncommitted_edits(path),
        path=path,
        from_named_pull_requests=merged,
    )


def locally(directory, url, role):
    path = directory if role is Role.UNDER_TEST else sibling(directory, url)
    return on_disk(repository_name(url) if url else directory.name, url, path, role)


def in_ci(url, reached, event, into, role):
    choice = picking.choose(url, repository_path(url), reached, event)
    heads = picking.place(url, choice, into)
    return Row(
        name=repository_name(url),
        repository=url,
        commit=git.local_commit(into, "HEAD"),
        how=choice.how,
        role=role,
        path=into,
        from_named_pull_requests=bool(choice.merging),
        merged_heads=tuple(
            MergedHead(head, entry.named.label, entry.base, entry.from_this_repository)
            for head, entry in zip(heads, choice.merging, strict=True)
        ),
    )


def not_used(reached):
    """A named pull request the run merges into nothing."""
    return [
        Row(
            name=repository_name(entry.named.path),
            repository=url_on_this_server(entry.named.path),
            commit=entry.head,
            how=f"{entry.named.label}, {entry.unused}",
            role=Role.NOT_USED,
            pull_request=entry.named.label,
        )
        for entry in reached
        if entry.unused is not None
    ]
