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


def clone_branch(url, path, branch, history=True):
    depth = () if history else ("--depth", "1")
    run = git("clone", "--quiet", *depth, "--branch", branch, url, str(path))
    if run.returncode != 0:
        raise unreachable(url, run)
    return path


def fetch(url, ref, path):
    run = git("fetch", "--quiet", url, ref, cwd=path)
    if run.returncode != 0:
        raise unreachable(url, run)
    return git("rev-parse", "FETCH_HEAD", cwd=path).stdout.strip()


def fetch_commit(url, commit, path):
    """The commit, fetched by its id; None where the server no longer serves it."""
    run = git("fetch", "--quiet", url, commit, cwd=path)
    fetched = git("rev-parse", "FETCH_HEAD", cwd=path).stdout.strip() if run.returncode == 0 else None
    return fetched if fetched == commit else None


def is_ancestor(path, commit, of="HEAD"):
    return git("merge-base", "--is-ancestor", commit, of, cwd=path).returncode == 0


def before_this_runs_merges(path):
    """HEAD as it was checked out, under the merges a run made on it, the hopped run's or the one before it."""
    for line in git("log", "--first-parent", "--format=%H %ce", "HEAD", cwd=path).stdout.splitlines():
        commit, _, committer = line.partition(" ")
        if committer != IDENTITY["GIT_COMMITTER_EMAIL"]:
            return commit
    return "HEAD"


def deepen(url, path):
    """The checkout's whole history where it holds one commit, as actions/checkout leaves it: a merge needs a base."""
    if git("rev-parse", "--is-shallow-repository", cwd=path).stdout.strip() != "true":
        return
    run = git("fetch", "--quiet", "--unshallow", url, cwd=path)
    if run.returncode != 0:
        raise unreachable(url, run)


def blob(path, commit, relative):
    """The bytes one file stands as at a commit, or None where the commit or the file is not there."""
    run = subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{relative}"],
        cwd=path,
        capture_output=True,
        env=dict(os.environ, GIT_TERMINAL_PROMPT="0", **IDENTITY),
    )
    return run.stdout if run.returncode == 0 else None


def merge(path, commit, name, *options):
    run = git("merge", "--no-edit", "--quiet", *options, commit, cwd=path)
    if run.returncode != 0:
        git("merge", "--abort", cwd=path)
        return f"{name} conflicts with what is already merged into {path.name}"
    return None


def toplevel(path):
    run = git("rev-parse", "--show-toplevel", cwd=path)
    return Path(run.stdout.strip()) if run.returncode == 0 else None
