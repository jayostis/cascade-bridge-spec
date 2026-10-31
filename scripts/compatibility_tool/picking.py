import os
import shutil
import stat
from dataclasses import dataclass, field

from compatibility_tool import git
from compatibility_tool.console import Stop
from compatibility_tool.github import Named, named_in, repository_path

NOTHING_CHECKED_OUT = "in a repository this run checks nothing out from"
THROUGH_ANOTHER = "reached only through another repository's pull request: name it on a Depends-On: line here to test the two together"


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
    def from_this_repository(self):
        head = (self.pull.get("head") or {}).get("repo") or {}
        base = (self.pull.get("base") or {}).get("repo") or {}
        return bool(base.get("full_name")) and head.get("full_name") == base.get("full_name")

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
    if named.is_in(event.repository):
        return THROUGH_ANOTHER  # until chained finds it on a line here
    return None if any(named.is_in(path) for path in merged_into) else NOTHING_CHECKED_OUT


def chained(api, event, reached):
    """Each pull request here named by the one under test, or by one so named, is merged into its checkout; one
    reached only through another repository's is not, so a pull request there does not bundle two here."""
    walking = [(event.under_test, api.pull_request(event.under_test))]
    seen = {event.under_test}
    while walking:
        holder, pull = walking.pop(0)
        for named in named_in(pull.get("body")):
            if named in seen or not named.is_in(event.repository):
                continue
            seen.add(named)
            entry = reached[named]
            entry.pull = api.pull_request(named)
            if not entry.open and not entry.pull.get("merged"):
                raise Stop(
                    f"{named.label} is closed without merging: cut the Depends-On: line naming it in {holder.label}"
                )
            if entry.open and not entry.from_this_repository:
                fork = ((entry.pull.get("head") or {}).get("repo") or {}).get("full_name") or "a fork"
                raise Stop(
                    f"{named.label} is from {fork}: a fork's pull request is not merged into the checkout under "
                    f"test, whose jobs may hold a write token; fold its changes into a pull request from "
                    f"{event.repository}"
                )
            entry.unused = None
            if entry.open:
                walking.append((named, entry.pull))


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
    chained(api, event, reached)
    return list(reached.values())


def merging(reached, path):
    return [entry for entry in reached if entry.unused is None and entry.open and entry.named.is_in(path)]


def numbered(entries):
    numbers = [f"#{entry.named.number}" for entry in entries]
    return numbers[0] if len(numbers) == 1 else " and ".join((", ".join(numbers[:-1]), numbers[-1]))


def partners(reached, event):
    """The pull requests chained to the one under test in its repository, merged or open, in the order of their
    numbers."""
    found = [entry for entry in reached if entry.named.is_in(event.repository) and entry.unused is None]
    return sorted(found, key=lambda entry: entry.named.number)


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
        plural = "s" if len(named) > 1 else ""
        return Choice(base, f"pull request{plural} {numbered(named)} merged into {base}", named)
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
    """The repository at its chosen branch, with every named pull request merged in; the heads merged, in order."""
    remove(into)  # an earlier run's checkout is not this run's version
    git.clone_branch(url, into, choice.branch, history=bool(choice.merging))
    heads = []
    for entry in choice.merging:
        head = git.fetch(url, f"refs/pull/{entry.named.number}/head", into)
        conflict = git.merge(into, head, entry.named.label)
        if conflict:
            raise Stop(conflict)
        heads.append(head)
    return heads
