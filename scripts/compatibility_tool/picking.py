import os
import shutil
import stat
from dataclasses import dataclass, field

from compatibility_tool import git
from compatibility_tool.console import Stop
from compatibility_tool.github import Named, named_in, repository_path

NOTHING_CHECKED_OUT = "in a repository this run checks nothing out from"
ALREADY_CHECKED_OUT = "in the repository under test, which this run does not merge it into"


@dataclass
class Reached:
    named: Named
    pull: dict
    unused: str | None = None

    @property
    def base(self):
        return self.pull.get("base", {}).get("ref")

    @property
    def head(self):
        return self.pull.get("head", {}).get("sha")

    @property
    def open(self):
        return not self.pull.get("merged") and self.pull.get("state") == "open"


@dataclass
class Choice:
    """A repository's version, before anything is fetched."""

    branch: str
    how: str
    merging: list[Reached] = field(default_factory=list)


def unused_where(named, event, merged_into):
    if named.path == event.repository:
        return ALREADY_CHECKED_OUT
    return None if named.path in merged_into else NOTHING_CHECKED_OUT


def follow(api, event, counterparts, specification):
    """Every pull request reached by Depends-On:, in the order reached.

    One the run merges into nothing is followed for its own lines and listed,
    and nothing about it fails the check.
    """
    if event.under_test is None:
        return []
    merged_into = {repository_path(url) for url in counterparts}
    if specification:
        merged_into.add(repository_path(specification))
    under_test = event.under_test
    reached = {}
    walking = [(api.pull_request(under_test), [under_test])]
    while walking:
        pull, path = walking.pop(0)
        for named in named_in(pull.get("body")):
            if named in path:
                continue
            unused = unused_where(named, event, merged_into)
            if named not in reached:
                found = api.pull_request(named, refuse=unused is None)
                if found is None:
                    reached[named] = Reached(named, {}, unused)
                    continue
                if unused is None and not found.get("merged") and found.get("state") != "open":
                    raise Stop(f"{named.label} is closed without merging, so nothing names a version of {named.path}")
                reached[named] = Reached(named, found, unused)
            entry = reached[named]
            if entry.open:
                walking.append((entry.pull, [*path, named]))
    return list(reached.values())


def merging(reached, path):
    return [entry for entry in reached if entry.unused is None and entry.open and entry.named.path == path]


def choose(url, path, reached, event):
    named = merging(reached, path)
    if named:
        bases = {entry.base for entry in named}
        if len(bases) != 1:
            raise Stop(
                f"pull requests named in {path} target one branch or the check cannot say which: "
                + ", ".join(f"{entry.named.label} targets {entry.base}" for entry in named)
            )
        base = bases.pop()
        numbers = [f"#{entry.named.number}" for entry in named]
        said = numbers[0] if len(numbers) == 1 else " and ".join((", ".join(numbers[:-1]), numbers[-1]))
        return Choice(base, f"pull request{'s' if len(numbers) > 1 else ''} {said} merged into {base}", named)
    running_on = event.branch
    if running_on and git.remote_branch(url, running_on):
        matching = "the branch matching the pull request's target" if event.number else "the branch this run is on"
        return Choice(running_on, f"{running_on}, {matching}")
    default = git.default_branch(url)
    return Choice(default, f"{default}, the default branch")


def remove(path):
    if not path.exists():
        return
    for root, _, files in os.walk(path):  # git's objects are read-only, and Windows refuses to unlink those
        for name in files:
            os.chmod(os.path.join(root, name), stat.S_IWRITE)
    shutil.rmtree(path)


def place(url, choice, into):
    """The repository at its chosen branch, with every named pull request merged in."""
    remove(into)  # an earlier run's checkout is not this run's version
    git.clone_branch(url, into, choice.branch)
    for entry in choice.merging:
        head = git.fetch(url, f"refs/pull/{entry.named.number}/head", into)
        conflict = git.merge(into, head, entry.named.label)
        if conflict:
            raise Stop(conflict)
    return into
