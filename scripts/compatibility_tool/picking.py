import os
import shutil
import stat
from dataclasses import dataclass, field

from compatibility_tool import git
from compatibility_tool.console import Stop
from compatibility_tool.github import Named, named_in


@dataclass
class Reached:
    named: Named
    pull: dict
    used: bool = True

    @property
    def base(self):
        return self.pull.get("base", {}).get("ref")

    @property
    def open(self):
        return not self.pull.get("merged") and self.pull.get("state") == "open"


@dataclass
class Choice:
    """A repository's version, before anything is fetched."""

    branch: str
    how: str
    merging: list[Reached] = field(default_factory=list)


def follow(api, under_test, checked_out):
    """Every pull request reached by Depends-On:, in the order reached.

    One in a repository the run checks nothing out from is followed for its own
    lines and listed, and nothing about it fails the check.
    """
    if under_test is None:
        return []
    reached = {}
    walking = [(api.pull_request(under_test), [under_test])]
    while walking:
        pull, path = walking.pop(0)
        for named in named_in(pull.get("body")):
            if named in path:
                raise Stop(
                    f"{' -> '.join(step.label for step in path)} -> {named.label} is a cycle of pull requests, "
                    "and a Depends-On: line goes one way"
                )
            used = named.path in checked_out
            if named not in reached:
                found = api.pull_request(named, refuse=used)
                if found is None:
                    reached[named] = Reached(named, {"number": named.number, "state": "unread"}, used=False)
                    continue
                if used and not found.get("merged") and found.get("state") != "open":
                    raise Stop(f"{named.label} is closed without merging, so nothing names a version of {named.path}")
                reached[named] = Reached(named, found, used=used)
            entry = reached[named]
            if entry.open:
                walking.append((entry.pull, [*path, named]))
    return list(reached.values())


def merging(reached, path):
    return [entry for entry in reached if entry.used and entry.open and entry.named.path == path]


def choose(url, path, reached, running_on, on_a_pull_request):
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
    if running_on and git.remote_branch(url, running_on):
        matching = "the branch matching the pull request's target" if on_a_pull_request else "the branch this run is on"
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


def place(url, path, choice, into):
    """The repository at its chosen branch, with every named pull request merged in."""
    remove(into)  # an earlier run's checkout is not this run's version
    git.clone_branch(url, into, choice.branch)
    for entry in choice.merging:
        head = git.fetch(url, f"refs/pull/{entry.named.number}/head", into)
        conflict = git.merge(into, head, entry.named.label)
        if conflict:
            raise Stop(conflict)
    return into
