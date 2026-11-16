"""The Bridge's build a runtime reads, placed in the runtime's cache with the run's token, which the runtime never holds."""

import hashlib
import http.client
import json
import os
import shutil
import tarfile
import tempfile
import urllib.error
from pathlib import Path

from compatibility_tool import git, releases
from compatibility_tool.console import Stop, note
from compatibility_tool.github import Unreadable, repository_path, url_on_this_server

BRIDGE = "jayostis/cascade-bridge-rs"
CACHE = Path("build") / "cache" / "cascade-bridge-rs"
KEPT_PICK = "picked.json"
HISTORY = 100
TAGS = "refs/tags/" + releases.TAG.format(commit="")


def built_commits(url):
    return {ref.removeprefix(TAGS) for ref in git.ls_remote(url, f"{TAGS}*") if not ref.endswith("^{}")}


def newest_built(url, built):
    tip = git.ls_remote(url, "HEAD").get("HEAD")
    if tip in built:
        return tip
    with tempfile.TemporaryDirectory() as history:
        git.git("init", "--quiet", cwd=history)
        fetched = git.git("fetch", "--quiet", f"--depth={HISTORY}", "--filter=tree:0", url, "HEAD", cwd=history)
        if fetched.returncode != 0:
            return None
        walked = git.git("rev-list", "--first-parent", "FETCH_HEAD", cwd=history)
        return next((commit for commit in walked.stdout.split() if commit in built), None)


def named_pull_requests(api):
    return [
        pull
        for named, pull in api.pulls.items()
        if named.is_in(BRIDGE) and not isinstance(pull, Unreadable) and pull.get("state") == "open"
    ]


def pick(api, event, url, built):
    """The commit a runtime would read the Bridge's build at and how it was picked, by the rule the runtime applies:
    the open pull request a Depends-On: line names, else the branch named like the run's, else the default
    branch's newest build. None where the runtime would stop or nothing has a build."""
    pulls = named_pull_requests(api)
    if pulls:
        head = pulls[0]["head"]["sha"] if len(pulls) == 1 else None
        return (head, "the head of the pull request a Depends-On: line names") if head in built else None
    if event.branch and event.branch != git.default_branch(url):
        head = git.remote_branch(url, event.branch)
        if head:
            return (head, f"the head of its branch {event.branch}") if head in built else None
    commit = newest_built(url, built)
    return None if commit is None else (commit, "the newest build of its default branch")


def fetched(api, commit):
    tag = releases.TAG.format(commit=commit)
    try:
        release = api.get(f"repos/{BRIDGE}/releases/tags/{tag}")
    except urllib.error.HTTPError as error:
        raise Stop(f"{tag} could not be read: {error}") from error
    archives = [asset for asset in release.get("assets") or [] if str(asset.get("name")).endswith(releases.ARCHIVES)]
    if len(archives) != 1:
        raise Stop(f"{release.get('tag_name')} holds {len(archives)} packages, not one")
    asset = archives[0]
    data = releases.download(asset["browser_download_url"])
    digest = f"sha256:{hashlib.sha256(data).hexdigest()}"
    if asset.get("digest") and asset["digest"] != digest:
        raise Stop(f"{asset['name']} is {digest}, which is not the digest {asset['digest']} the release gives")
    return data


def recorded(folder):
    try:
        return json.loads((folder / "package.json").read_text(encoding="utf-8"))["cascadeBridge"]["commit"]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def place(runtime, api, event):
    """The pick's release unpacked under the runtime's cache, and the pick kept as the runtime keeps its own, so that
    the runtime reads this build and asks GitHub for none. A run that cannot place it leaves the runtime to its own."""
    url = url_on_this_server(repository_path(BRIDGE))
    try:
        found = pick(api, event, url, built_commits(url))
        if found is None:
            note("no build of the Bridge could be picked here, so the runtime picks its own")
            return
        commit, how = found
        at = runtime / CACHE
        folder = at / releases.TAG.format(commit=commit)
        if recorded(folder) != commit:
            releases.unpack(fetched(api, commit), folder)
            if recorded(folder) != commit:
                shutil.rmtree(folder, ignore_errors=True)
                raise Stop(f"the package of {commit} records no build of it")
        attempt = f"{os.environ.get('GITHUB_RUN_ID', '')}.{os.environ.get('GITHUB_RUN_ATTEMPT') or '1'}"
        if os.environ.get("GITHUB_RUN_ID"):
            (at / KEPT_PICK).write_text(
                json.dumps({"attempt": attempt, "repository": url, "commit": commit, "how": how}), encoding="utf-8"
            )
        print(f"  bridge build {commit}, {how}, placed in {CACHE.as_posix()}   (read with the run's token)")
    except (urllib.error.URLError, http.client.HTTPException, tarfile.TarError, OSError, ValueError, Stop) as error:
        note(f"the Bridge's build could not be placed ({error}), so the runtime picks and reads its own")
