import os
import subprocess
from pathlib import Path

from compatibility_tool.console import Stop, first_line

IDENTITY = {
    "GIT_AUTHOR_NAME": "cascade compatibility",
    "GIT_AUTHOR_EMAIL": "compatibility@invalid",
    "GIT_COMMITTER_NAME": "cascade compatibility",
    "GIT_COMMITTER_EMAIL": "compatibility@invalid",
}


def git(*args, cwd=None):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never", **IDENTITY),
    )


def unreachable(url, run):
    return Stop(
        f"{url} could not be reached: it may be private, renamed or deleted, "
        f"or the network refused (git: {first_line(run.stderr)})"
    )


def ls_remote(url, *patterns):
    run = git("ls-remote", url, *patterns)
    if run.returncode != 0:
        raise unreachable(url, run)
    return {ref: sha for sha, _, ref in (line.partition("\t") for line in run.stdout.splitlines())}


def remote_branch(url, branch):
    return ls_remote(url, f"refs/heads/{branch}").get(f"refs/heads/{branch}")


def default_branch(url):
    run = git("ls-remote", "--symref", url, "HEAD")
    if run.returncode != 0:
        raise unreachable(url, run)
    for line in run.stdout.splitlines():
        if line.startswith("ref: refs/heads/"):
            return line.removeprefix("ref: refs/heads/").split("\t", 1)[0]
    raise Stop(f"{url} names no default branch")


def local_commit(path, ref):
    run = git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", cwd=path)
    return run.stdout.strip() if run.returncode == 0 else None


def current_branch(path):
    return git("symbolic-ref", "--quiet", "--short", "HEAD", cwd=path).stdout.strip()


def has_uncommitted_edits(path):
    return bool(git("status", "--porcelain", cwd=path).stdout.strip())


def clone_branch(url, path, branch):
    run = git("clone", "--quiet", "--branch", branch, url, str(path))
    if run.returncode != 0:
        raise unreachable(url, run)
    return path


def clone_at(url, path, commit):
    """The repository cloned and left detached at one commit; false where it holds no such commit."""
    run = git("clone", "--quiet", "--no-checkout", url, str(path))
    if run.returncode != 0:
        raise unreachable(url, run)
    return git("checkout", "--quiet", "--detach", commit, cwd=path).returncode == 0


def init(path):
    run = git("init", "--quiet", str(path))
    if run.returncode != 0:
        raise Stop(f"{path} could not be made a repository to read from (git: {first_line(run.stderr)})")
    return path


def fetch(url, ref, path):
    run = git("fetch", "--quiet", url, ref, cwd=path)
    if run.returncode != 0:
        raise unreachable(url, run)
    return git("rev-parse", "FETCH_HEAD", cwd=path).stdout.strip()


def fetched(url, ref, path):
    return git("fetch", "--quiet", url, ref, cwd=path).returncode == 0


def holds(path, commit, other):
    return git("merge-base", "--is-ancestor", other, commit, cwd=path).returncode == 0


def blob(path, commit, relative):
    """The bytes one file stands as at a commit, or None where the commit or the file is not there."""
    run = subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{relative}"],
        cwd=path,
        capture_output=True,
        env=dict(os.environ, GIT_TERMINAL_PROMPT="0", **IDENTITY),
    )
    return run.stdout if run.returncode == 0 else None


def merge(path, commit, name):
    run = git("merge", "--no-edit", "--quiet", commit, cwd=path)
    if run.returncode != 0:
        git("merge", "--abort", cwd=path)
        return f"{name} conflicts with what is already merged into {path.name}"
    return None


def toplevel(path):
    run = git("rev-parse", "--show-toplevel", cwd=path)
    return Path(run.stdout.strip()) if run.returncode == 0 else None
