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
    """owner/repository, the two last segments of a repository URL."""
    segments = [segment for segment in urlparse(url).path.split("/") if segment]
    if len(segments) < 2:
        raise Stop(f"{url} names no owner and repository")
    owner, repository = segments[-2], segments[-1]
    return f"{owner}/{repository.removesuffix('.git')}"


def repository_name(url):
    return repository_path(url).split("/")[-1]


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


class Api:
    def __init__(self, url=None, token=None):
        self.url = (url or os.environ.get("GITHUB_API_URL") or "https://api.github.com").rstrip("/")
        self.token = token if token is not None else os.environ.get("GITHUB_TOKEN", "")
        self.pulls = {}

    def request(self, method, path, body=None):
        request = urllib.request.Request(
            f"{self.url}/{path}",
            method=method,
            data=json.dumps(body).encode("utf-8") if body is not None else None,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "cascade-compatibility",
                **({"Authorization": f"Bearer {self.token}"} if self.token else {}),
                **({"Content-Type": "application/json"} if body is not None else {}),
            },
        )
        with urllib.request.urlopen(request) as answer:
            return json.loads(answer.read().decode("utf-8") or "{}")

    def pull_request(self, named):
        if named not in self.pulls:
            try:
                self.pulls[named] = self.request("GET", f"repos/{named.path}/pulls/{named.number}")
            except urllib.error.HTTPError as error:
                raise Stop(f"{named.label} could not be read: {error.code} {error.reason}") from error
        return self.pulls[named]

    def comment(self, path, number, body):
        self.request("POST", f"repos/{path}/issues/{number}/comments", {"body": body})


@dataclass(frozen=True)
class Event:
    """What the workflow run says it is running on."""

    repository: str
    number: int | None
    branch: str

    @property
    def under_test(self):
        return Named(self.repository, self.number) if self.number else None


def event():
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    branch = os.environ.get("GITHUB_REF_NAME", "")
    path = os.environ.get("GITHUB_EVENT_PATH")
    payload = {}
    if path and os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    pull_request = payload.get("pull_request") or {}
    number = pull_request.get("number")
    return Event(repository, number, pull_request.get("base", {}).get("ref") or branch)
