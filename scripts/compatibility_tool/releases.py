"""A counterpart engine's host run from the assets of the release built from its commit, in place of its setup."""

import base64
import binascii
import fnmatch
import hashlib
import http.client
import io
import json
import platform
import re
import shutil
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from compatibility_tool import git, github
from compatibility_tool.console import Stop, note
from compatibility_tool.document import FILE, hosts

TAG = "build-{commit}"
PACKAGED = "package/"
ARCHIVES = (".tgz", ".tar.gz")
SUBRESOURCE_INTEGRITY = re.compile(r"^(sha256|sha384|sha512)-([A-Za-z0-9+/=]+)$")
HEX_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
DOWNLOAD_TIMEOUT_SECONDS = 60
POLL_SECONDS = 15
POLL_TIMEOUT_SECONDS = 30
LAST_LOOK_SECONDS = 5
WAIT_SECONDS = 6 * 60
RUNS_THAT_RELEASE = ("push", "pull_request")
sleep = time.sleep
monotonic = time.monotonic


def on_a_runner_releases_serve():
    return platform.system() == "Linux" and platform.machine() in ("x86_64", "AMD64")


def hosts_at(path, commit):
    try:
        document = json.loads(git.blob(path, commit, FILE) or b"null")
    except ValueError:
        return None
    return {host.get("name"): host for host in hosts(document) if isinstance(host, dict)}


def set_up_alike(path, branch):
    """Whether each host declaring a release has the setup here that it has at the branch, which built its release."""
    here, there = hosts_at(path, "HEAD"), hosts_at(path, branch)
    if here is None or there is None:
        return False
    return all(
        name in there and there[name].get("setup") == host.get("setup")
        for name, host in here.items()
        if "release" in host
    )


def the_branchs_commit(row):
    """The branch's commit, where the pull requests merged into the engine change nothing but its compatibility.json
    and no setup in it; None where they do."""
    branch = git.local_commit(row.path, "@{upstream}")
    if branch is None:
        return None
    changed = git.git("diff", "--name-only", branch, "HEAD", cwd=row.path)
    if changed.returncode != 0 or set(changed.stdout.split()) - {FILE}:
        return None
    return branch if set_up_alike(row.path, branch) else None


def a_head_merged(row):
    return any(merged.commit == row.commit for merged in row.merged_heads)


def released_commit(row):
    """The commit whose release holds this engine's build: its own, the branch's where the pull requests merged into
    it change nothing but its compatibility.json, or, where the merge fast-forwarded, the pull request's head; None
    where it is to be built."""
    if row.uncommitted_edits or not row.commit or row.path is None:
        return None
    if not row.from_named_pull_requests:
        return row.commit
    return the_branchs_commit(row) or (row.commit if a_head_merged(row) else None)


def say_how_to_stop_merging(row):
    """A single pull request the run merged, rather than fast-forwarded to, is told to catch up with its base."""
    if row.uncommitted_edits or not row.commit or row.path is None or len(row.merged_heads) != 1:
        return
    [merged] = row.merged_heads
    if row.commit == git.local_commit(row.path, "@{upstream}"):
        return
    note(
        f"{merged.label} is behind {merged.base}, so {row.name} is a merge made by this run, which no release holds: "
        f"bring it up to date (git merge origin/{merged.base}, then push) to run from "
        f"{TAG.format(commit=merged.commit)}"
    )


def unfinished_runs(api, path, commit, timeout):
    """The pages of the engine's runs at the commit that are not done and that a push or a pull request started."""
    found = api.get(f"{path}/actions/runs?head_sha={commit}&per_page=100", timeout=timeout)
    return [
        str(run.get("html_url") or run.get("id"))
        for run in found.get("workflow_runs") or []
        if run.get("event") in RUNS_THAT_RELEASE and run.get("status") != "completed"
    ]


def from_a_fork(row, commit):
    return any(merged.commit == commit and not merged.from_this_repository for merged in row.merged_heads)


def release_being_made(api, row, path, tag, commit):
    """The release, once it appears while a run of the engine at the commit is unfinished; None where it does not.
    After the last sleep the release is looked for once more, so one published in the final seconds is used."""
    started = monotonic()
    deadline = started + WAIT_SECONDS
    unfinished = None
    while True:
        left = deadline - monotonic()
        try:
            now_unfinished = unfinished_runs(api, path, commit, min(POLL_TIMEOUT_SECONDS, max(left, LAST_LOOK_SECONDS)))
        except (OSError, http.client.HTTPException, ValueError, Stop) as error:
            note(f"the runs of {row.name} at {commit} could not be read ({error}), so each host is built by its setup")
            return None
        if not now_unfinished:
            note(f"{row.name} has no release {tag} and no run at {commit} to make one, so each host is built")
            return None
        if unfinished is None:
            note(f"{tag} is not there yet: waiting up to {WAIT_SECONDS // 60} min for {', '.join(now_unfinished)}")
        unfinished = now_unfinished
        sleep(max(0, min(POLL_SECONDS, deadline - monotonic())))
        left = deadline - monotonic()
        try:
            found = api.get(
                f"{path}/releases/tags/{tag}", timeout=min(POLL_TIMEOUT_SECONDS, max(left, LAST_LOOK_SECONDS))
            )
            note(f"{tag} appeared after {round(monotonic() - started)} s")
            return found
        except urllib.error.HTTPError as error:
            if error.code != 404:
                note(f"{row.name} has no release {tag} to read ({error}), so each host is built by its setup")
                return None
        except (OSError, http.client.HTTPException, ValueError, Stop) as error:
            note(f"{tag} could not be read ({error}), so each host is built by its setup")
            return None
        if left <= 0:
            note(f"waited {WAIT_SECONDS // 60} min for {tag}; {', '.join(unfinished)} had not finished")
            return None


def release_at(api, row, path, commit, wait=True):
    """The release built from the commit; None where there is none to run."""
    tag = TAG.format(commit=commit)
    try:
        return api.get(f"{path}/releases/tags/{tag}")
    except urllib.error.HTTPError as error:
        if error.code == 404 and wait and not from_a_fork(row, commit):
            return release_being_made(api, row, path, tag, commit)
        note(f"{row.name} has no release {tag} to read ({error}), so each host is built by its setup")
    except (OSError, http.client.HTTPException, ValueError, Stop) as error:
        note(f"{row.name} has no release {tag} to read ({error}), so each host is built by its setup")
    return None


def release_of(row):
    """The release built from the engine's commit; None where there is none to run. Where the branch's release is
    missing, the head the run fast-forwarded to may have one."""
    if not on_a_runner_releases_serve():
        return None
    commit = released_commit(row)
    if commit is None:
        say_how_to_stop_merging(row)
        return None
    path = f"repos/{github.repository_path(row.repository)}"
    api = github.Api()
    found = release_at(api, row, path, commit)
    if found is None and commit != row.commit and a_head_merged(row):
        found = release_at(api, row, path, row.commit, wait=False)
    return found


def digests(notes):
    for line in (notes or "").splitlines():
        _, _, value = line.partition(":")
        value = value.strip()
        integrity = SUBRESOURCE_INTEGRITY.match(value)
        if integrity:
            try:
                yield integrity[1], base64.b64decode(integrity[2], validate=True)
            except binascii.Error:
                continue
        elif HEX_SHA256.match(value):
            yield "sha256", bytes.fromhex(value)


def vouched_for(data, notes):
    return any(hashlib.new(algorithm, data).digest() == digest for algorithm, digest in digests(notes))


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": "cascade-compatibility"})
    with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as answer:
        return answer.read()


def unpack(data, into):
    """The archive's package laid at into, which is left as it was where the archive cannot be unpacked."""
    into.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(dir=into.parent))
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            members = []
            for member in archive.getmembers():
                if member.name.startswith(PACKAGED) and member.name != PACKAGED:
                    member.name = member.name.removeprefix(PACKAGED)
                    if member.islnk():
                        member.linkname = member.linkname.removeprefix(PACKAGED)
                    members.append(member)
            archive.extractall(staged, members=members, filter="data")
    except BaseException:
        shutil.rmtree(staged, ignore_errors=True)
        raise
    shutil.rmtree(into, ignore_errors=True)
    staged.rename(into)


def place(data, name, into):
    if name.endswith(ARCHIVES):
        unpack(data, into)
        return
    into.parent.mkdir(parents=True, exist_ok=True)
    into.write_bytes(data)
    into.chmod(0o755)


def placed(release, engine, host):
    """The host's command, once the asset its release names is placed in the engine; None where the setup runs."""
    declared = host.get("release")
    if release is None or not isinstance(declared, dict):
        return None
    name = host.get("name")
    assets = [
        asset
        for asset in release.get("assets") or []
        if fnmatch.fnmatchcase(str(asset.get("name")), str(declared.get("asset")))
    ]
    if len(assets) != 1:
        note(f"{release.get('tag_name')} holds {len(assets)} assets named {declared.get('asset')}, so {name} is built")
        return None
    asset = assets[0]
    into = (engine / str(declared.get("path"))).resolve()
    if into == engine.resolve() or not into.is_relative_to(engine.resolve()):
        note(f"{declared.get('path')} is no path in {engine}, so {name} is built")
        return None
    try:
        data = download(asset["browser_download_url"])
    except (urllib.error.URLError, http.client.HTTPException, OSError, KeyError) as error:
        note(f"{asset['name']} could not be downloaded ({error}), so {name} is built")
        return None
    if not vouched_for(data, release.get("body")):
        note(f"{asset['name']} matches no digest the notes of {release.get('tag_name')} give, so {name} is built")
        return None
    try:
        place(data, asset["name"], into)
    except (tarfile.TarError, OSError) as error:
        note(f"{asset['name']} could not be placed at {declared.get('path')} ({error}), so {name} is built")
        return None
    print(f"  release {asset['name']} of {release.get('tag_name')}, placed at {Path(declared['path'])}   (for {name})")
    return declared.get("command") or host.get("command")
