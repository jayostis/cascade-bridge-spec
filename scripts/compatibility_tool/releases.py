"""A counterpart engine's host run from the assets of the release built from its commit, in place of its setup."""

import base64
import binascii
import fnmatch
import hashlib
import io
import platform
import re
import shutil
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

from compatibility_tool import git, github
from compatibility_tool.console import Stop, note
from compatibility_tool.document import FILE

TAG = "build-{commit}"
PACKAGED = "package/"
ARCHIVES = (".tgz", ".tar.gz")
SUBRESOURCE_INTEGRITY = re.compile(r"^(sha256|sha384|sha512)-([A-Za-z0-9+/=]+)$")
HEX_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def on_a_runner_releases_serve():
    return platform.system() == "Linux" and platform.machine() in ("x86_64", "AMD64")


def released_commit(row):
    """The commit whose release holds this engine's build: its own, or, where the pull requests merged into it change
    nothing but its compatibility.json, the branch's; None where it is to be built."""
    if row.uncommitted_edits or not row.commit or row.path is None:
        return None
    if not row.from_named_pull_requests:
        return row.commit
    branch = git.local_commit(row.path, "@{upstream}")
    if branch is None:
        return None
    changed = git.git("diff", "--name-only", branch, "HEAD", cwd=row.path)
    if changed.returncode != 0 or set(changed.stdout.split()) - {FILE}:
        return None
    return branch


def release_of(row):
    """The release built from the engine's commit, with that commit; None where there is none to run."""
    commit = released_commit(row) if on_a_runner_releases_serve() else None
    if commit is None:
        return None
    tag = TAG.format(commit=commit)
    try:
        return github.Api().get(f"repos/{github.repository_path(row.repository)}/releases/tags/{tag}")
    except (urllib.error.HTTPError, Stop) as error:
        note(f"{row.name} has no release {tag} to read ({error}), so each host is built by its setup")
        return None


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
    with urllib.request.urlopen(request) as answer:
        return answer.read()


def unpack(data, into):
    shutil.rmtree(into, ignore_errors=True)
    into.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        members = []
        for member in archive.getmembers():
            if member.name.startswith(PACKAGED) and member.name != PACKAGED:
                member.name = member.name.removeprefix(PACKAGED)
                members.append(member)
        archive.extractall(into, members=members, filter="data")


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
    if not into.is_relative_to(engine.resolve()):
        note(f"{declared.get('path')} is no path in {engine}, so {name} is built")
        return None
    try:
        data = download(asset["browser_download_url"])
    except (urllib.error.URLError, OSError, KeyError) as error:
        note(f"{asset['name']} could not be downloaded ({error}), so {name} is built")
        return None
    if not vouched_for(data, release.get("body")):
        note(f"{asset['name']} matches no digest the notes of {release.get('tag_name')} give, so {name} is built")
        return None
    place(data, asset["name"], into)
    print(f"  release {asset['name']} of {release.get('tag_name')}, placed at {Path(declared['path'])}   (for {name})")
    return declared.get("command") or host.get("command")
