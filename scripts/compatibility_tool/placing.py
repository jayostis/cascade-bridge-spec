from compatibility_tool import git, picking
from compatibility_tool.console import Stop
from compatibility_tool.github import repository_name, repository_path, url_on_this_server
from compatibility_tool.record import Role, Row


def sibling(directory, url):
    path = directory.parent / repository_name(url)
    if not (path / ".git").exists():
        raise Stop(f"{url} has no clone beside {directory.name}; clone it with: git clone {url} {path}")
    return path


def toplevel(directory, fallback):
    return git.toplevel(directory) or fallback


def under_test_is(event):
    if event.number:
        return f"pull request #{event.number} merged into {event.branch}"
    return f"{event.branch}, the branch this run is on"


def working_tree_is(path, role):
    branch = git.current_branch(path) or "a detached HEAD"
    where = "its working tree" if role is Role.UNDER_TEST else "the sibling's working tree"
    return f"{where}, on {branch}"


def on_disk(name, url, path, role, how=None):
    return Row(
        name=name,
        repository=url,
        commit=git.local_commit(path, "HEAD"),
        how=how or working_tree_is(path, role),
        role=role,
        uncommitted_edits=git.has_uncommitted_edits(path),
        path=path,
    )


def locally(directory, url, role):
    path = directory if role is Role.UNDER_TEST else sibling(directory, url)
    return on_disk(repository_name(url) if url else directory.name, url, path, role)


def in_ci(url, reached, event, into, role):
    choice = picking.choose(url, repository_path(url), reached, event)
    picking.place(url, choice, into)
    return Row(
        name=repository_name(url),
        repository=url,
        commit=git.local_commit(into, "HEAD"),
        how=choice.how,
        role=role,
        path=into,
        from_named_pull_requests=bool(choice.merging),
    )


def pinned(directory, url, commit, role, how, options, event, reached):
    """A repository pinned by commit: the sibling locally; in CI, the pull requests named of it, otherwise the pin."""
    name = repository_name(url)
    if options.mode == "local":
        return on_disk(name, url, sibling(directory, url), role)
    into = directory.parent / name
    if picking.merging(reached, repository_path(url)):
        return in_ci(url, reached, event, into, role)
    picking.remove(into)
    if not git.clone_at(url, into, commit):
        raise Stop(f"{url} holds no commit {commit}, which is what {how} names")
    return Row(name=name, repository=url, commit=commit, how=how, role=role, path=into)


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
