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

    @property
    def base(self):
        return self.pull.get("base", {}).get("ref")


@dataclass
class Choice:
    """A repository's version, before anything is fetched."""

    branch: str
    how: str
    merging: list[Reached] = field(default_factory=list)


def follow(api, under_test):
    """Every open pull request reached by Depends-On:, in the order reached."""
    if under_test is None:
        return []
    reached = []
    seen = {under_test}
    walking = [(under_test, api.pull_request(under_test), [under_test])]
    while walking:
        _, pull, path = walking.pop(0)
        for named in named_in(pull.get("body")):
            if named in path:
                raise Stop(
                    f"{named.label} is named by a cycle of pull requests: {' -> '.join(step.label for step in path)} -> {named.label}"
                )
            if named in seen:
                continue
            seen.add(named)
            found = api.pull_request(named)
            if found.get("merged"):
                reached.append(Reached(named, found))
                continue
            if found.get("state") != "open":
                raise Stop(f"{named.label} is closed without merging, so nothing names a version of {named.path}")
            reached.append(Reached(named, found))
            walking.append((named, found, [*path, named]))
    return reached


def merging(reached, path):
    return [entry for entry in reached if entry.named.path == path and not entry.pull.get("merged")]


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
    def writable(function, name, _):  # git's objects are read-only, and Windows refuses to unlink those
        os.chmod(name, stat.S_IWRITE)
        function(name)

    shutil.rmtree(path, onexc=writable) if path.exists() else None


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
