from compatibility_tool import git, picking
from compatibility_tool.console import Stop
from compatibility_tool.github import repository_name, repository_path
from compatibility_tool.record import Role, Used


def sibling(directory, url):
    path = directory.parent / repository_name(url)
    if not (path / ".git").exists():
        raise Stop(f"{url} has no clone beside {directory.name}; clone it with: git clone {url} {path}")
    return path


def on_disk(name, url, path, role):
    branch = git.current_branch(path) or "a detached HEAD"
    where = "its working tree" if role is Role.UNDER_TEST else "the sibling's working tree"
    return Used(
        name=name,
        repository=url,
        commit=git.local_commit(path, "HEAD"),
        how=f"{where}, on {branch}",
        role=role,
        uncommitted_edits=git.has_uncommitted_edits(path),
        path=path,
    )


def locally(directory, url, role):
    path = directory if role is Role.UNDER_TEST else sibling(directory, url)
    name = repository_name(url) if url else directory.name
    return on_disk(name, url, path, role)


def in_ci(url, reached, running_on, on_a_pull_request, into, role):
    choice = picking.choose(url, repository_path(url), reached, running_on, on_a_pull_request)
    picking.place(url, repository_path(url), choice, into)
    return Used(
        name=repository_name(url),
        repository=url,
        commit=git.local_commit(into, "HEAD"),
        how=choice.how,
        role=role,
        path=into,
    )
