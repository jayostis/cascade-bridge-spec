import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

from compatibility_tool.console import Stop

DEPENDS_ON = re.compile(r"^\s*Depends-On:\s*(\S+)\s*$", re.IGNORECASE | re.MULTILINE)
PULL_REQUEST_URL = re.compile(
    r"^(?:https?://[^/]+/)?(?P<owner>[^/\s]+)/(?P<repository>[^/\s]+)/pull/(?P<number>\d+)/?$"
)


def repository_path(url):
    segments = [segment for segment in urlparse(url).path.split("/") if segment]
    if len(segments) < 2:
        raise Stop(f"{url} names no owner and repository")
    owner, repository = segments[-2], segments[-1]
    return f"{owner}/{repository.removesuffix('.git')}"


def repository_name(url):
    return repository_path(url).split("/")[-1]


def url_on_this_server(path):
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    return f"{server}/{path}"


@dataclass(frozen=True)
class Named:
    """A pull request a description names on a Depends-On: line."""

    path: str
    number: int

    @property
    def label(self):
        return f"{self.path}/pull/{self.number}"


def named_in(description):
    named = []
    for reference in DEPENDS_ON.findall(description or ""):
        match = PULL_REQUEST_URL.match(reference)
        if not match:
            raise Stop(
                f"Depends-On: {reference} names no pull request, as https://github.com/owner/repository/pull/1 does"
            )
        entry = Named(f"{match['owner']}/{match['repository']}", int(match["number"]))
        if entry not in named:
            named.append(entry)
    return named


@dataclass(frozen=True)
class Unreadable:
    said: str


class Api:
    def __init__(self):
        self.url = (os.environ.get("GITHUB_API_URL") or "https://api.github.com").rstrip("/")
        self.token = os.environ.get("GITHUB_TOKEN", "")  # start empties it; a local run may have one
        self.pulls = {}

    def get(self, path):
        request = urllib.request.Request(
            f"{self.url}/{path}",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "cascade-compatibility",
                **({"Authorization": f"Bearer {self.token}"} if self.token else {}),
            },
        )
        try:
            with urllib.request.urlopen(request) as answer:
                return json.loads(answer.read().decode("utf-8") or "{}")
        except urllib.error.URLError as error:
            if isinstance(error, urllib.error.HTTPError):
                raise
            raise Stop(f"{self.url} could not be reached: {error.reason}") from error

    def pull_request(self, named, refuse=True):
        """None where the run reads a pull request it uses nothing from and cannot."""
        if named not in self.pulls:
            try:
                self.pulls[named] = self.get(f"repos/{named.path}/pulls/{named.number}")
            except urllib.error.HTTPError as error:
                self.pulls[named] = Unreadable(f"{error.code} {error.reason}")
        found = self.pulls[named]
        if isinstance(found, Unreadable):
            if refuse:  # a later reader may want what an earlier one could do without
                raise Stop(f"{named.label} could not be read: {found.said}")
            return None
        return found


@dataclass(frozen=True)
class Event:
    repository: str
    number: int | None
    branch: str

    @property
    def under_test(self):
        return Named(self.repository, self.number) if self.number else None


def event(api):
    """The pull request's number from the event that started the run; its branch from the API, read now."""
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    branch = os.environ.get("GITHUB_REF_NAME", "")
    path = os.environ.get("GITHUB_EVENT_PATH")
    payload = {}
    if path and os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as handle:
                payload = json.load(handle)
        except ValueError as error:
            raise Stop(f"{path}, the event the run started from, is not JSON: {error}") from error
    number = (payload.get("pull_request") or {}).get("number")
    if not number:
        return Event(repository, None, branch)
    pull = api.pull_request(Named(repository, number))
    return Event(repository, number, pull.get("base", {}).get("ref") or branch)
