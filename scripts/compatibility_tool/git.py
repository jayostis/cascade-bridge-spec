import os
import shutil
import subprocess
from pathlib import Path

from compatibility_tool.console import Stop, first_line


def git(*args, cwd=None):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never"),
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


def remote_tag_commit(url, tag):
    refs = ls_remote(url, f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}")
    return refs.get(f"refs/tags/{tag}^{{}}") or refs.get(f"refs/tags/{tag}")


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


def worktree_at(repository, tree, commit):
    if tree.exists():
        if local_commit(tree, "HEAD") == commit:
            return tree
        git("worktree", "remove", "--force", str(tree), cwd=repository)
        shutil.rmtree(tree, ignore_errors=True)
        git("worktree", "prune", cwd=repository)
    tree.parent.mkdir(parents=True, exist_ok=True)
    run = git("worktree", "add", "--detach", "--quiet", str(tree), commit, cwd=repository)
    if run.returncode != 0:
        raise Stop(f"git made no worktree of {repository} at {commit}: {first_line(run.stderr)}")
    return tree


def clone_at(url, path, commit):
    run = git("clone", "--quiet", "--no-checkout", "--filter=blob:none", url, str(path))
    if run.returncode != 0:
        raise unreachable(url, run)
    run = git("checkout", "--quiet", "--detach", commit, cwd=path)
    if run.returncode != 0:
        raise Stop(f"{url} does not hold {commit}: {first_line(run.stderr)}")
    return path


class Ancestry:
    def __init__(self, scratch):
        self.scratch = Path(scratch)
        self.fetched = {}

    def on(self, url, branch, commit):
        repository = self.fetched.get(url)
        if repository is None:
            repository = self.scratch / f"counterpart-{len(self.fetched)}"
            git("init", "--quiet", "--bare", str(repository))
            run = git(
                "fetch",
                "--quiet",
                "--filter=blob:none",
                url,
                f"+refs/heads/{branch}:refs/heads/{branch}",
                cwd=repository,
            )
            if run.returncode != 0:
                raise unreachable(url, run)
            self.fetched[url] = repository
        return git("merge-base", "--is-ancestor", commit, f"refs/heads/{branch}", cwd=repository).returncode == 0
