#!/usr/bin/env python3
"""Tests for scripts/compatibility.py, in the pattern of selftest-lint.py.

The question is the same one: *what would the tool report if the thing it
claims to check were wrong?* Each case builds a small world, breaks one property
of it or exercises one rule, and asserts the tool's exit status and the words it
says. The first cases show it passing, so that a red case is known to be red for
its own reason.

**No network.** The counterparts are throwaway git repositories made in a
temporary directory: an `origins` directory standing for where repositories are
published, named by file:// URLs, and a `workspace` directory holding clones of
them side by side, as compatibility.md lays siblings out. Commits, tags, a
default branch and a feature branch are made there, so resolving, checking out
and the merge-time rule run against real git without reaching GitHub.

**Nothing here mutates a tracked file.** fixtures/synthetic-adapter is copied,
never edited, and no case writes inside the repository. No real adapter or
engine is named: the counterparts are this repository's own fixtures, under
names this file makes up.

Each tool run gets the case's temporary directory as its system temporary
directory, so the record, and any worktree the tool makes, land there and go
with it.

Run:  python3 scripts/selftest-compatibility.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SPEC_ROOT = Path(__file__).resolve().parent.parent
TOOL = SPEC_ROOT / "scripts" / "compatibility.py"
ADAPTER = SPEC_ROOT / "fixtures" / "synthetic-adapter"
CONTEXT_IRI = "https://ns.cascadeprotocol.org/bridge/v1-draft/compatibility.jsonld"

IDENTITY = [
    "-c", "user.name=selftest",
    "-c", "user.email=selftest@example.org",
    "-c", "commit.gpgsign=false",
    "-c", "tag.gpgsign=false",
]


class SelfTestFailure(AssertionError):
    pass


def git(*args, cwd=None):
    run = subprocess.run(
        ["git", *IDENTITY, *args], cwd=cwd, capture_output=True, text=True
    )
    if run.returncode != 0:
        raise SelfTestFailure(f"git {' '.join(args)}: {run.stderr.strip()}")
    return run.stdout.strip()


# ---------------------------------------------------------------------------
# The world a case runs in
# ---------------------------------------------------------------------------


class World:
    """Published repositories under origins/, and a workspace of clones.

    specification  one commit on main: what an engine's specification pins
    adapter        a copy of fixtures/synthetic-adapter: main, tag v1 on main,
                   and a feature branch feat/next one commit ahead of main
    engine         an engine's repository, holding whatever the case needs
    """

    def __init__(self, root):
        self.root = Path(root)
        self.origins = self.root / "origins"
        self.workspace = self.root / "workspace"
        self.origins.mkdir()
        self.workspace.mkdir()
        self.commits = {}

        self.publish("specification", lambda path: (path / "README.md").write_text(
            "a stand-in for the specification\n", encoding="utf-8"
        ))
        self.commits["specification"] = self.head("specification")

        self.publish("adapter", lambda path: shutil.copytree(
            ADAPTER, path, dirs_exist_ok=True
        ))
        self.commits["adapter"] = self.head("adapter")
        git("tag", "-a", "v1", "-m", "v1", cwd=self.origins / "adapter")
        git("checkout", "-q", "-b", "feat/next", cwd=self.origins / "adapter")
        (self.origins / "adapter" / "NOTICE").write_text("next\n", encoding="utf-8")
        git("add", "-A", cwd=self.origins / "adapter")
        git("commit", "-q", "-m", "feat: next", cwd=self.origins / "adapter")
        self.commits["adapter feat/next"] = self.head("adapter")
        git("checkout", "-q", "main", cwd=self.origins / "adapter")

        self.publish("engine", lambda path: (path / "README.md").write_text(
            "an engine\n", encoding="utf-8"
        ))

    def publish(self, name, fill):
        path = self.origins / name
        path.mkdir()
        fill(path)
        git("init", "-q", "-b", "main", str(path))
        git("add", "-A", cwd=path)
        git("commit", "-q", "-m", f"{name}: first", cwd=path)

    def head(self, name):
        return git("rev-parse", "HEAD", cwd=self.origins / name)

    def url(self, name):
        return (self.origins / name).as_uri()

    def clone(self, name):
        path = self.workspace / name
        git("clone", "-q", self.url(name), str(path))
        return path


def write_file(directory, document):
    body = {"@context": CONTEXT_IRI, **document}
    (directory / "compatibility.json").write_text(
        json.dumps(body, indent=2) + "\n", encoding="utf-8", newline=""
    )


def engine_file(world, tested_with, **overrides):
    """An engine's compatibility.json. The vectors name the running interpreter,
    so the case runs where python3 is not on PATH."""
    document = {
        "specification": {
            "codeRepository": world.url("specification"),
            "commit": world.commits["specification"],
        },
        "setup": [sys.executable, "-c", "pass"],
        "command": [sys.executable, "-c", "pass"],
        "testedWith": tested_with,
    }
    document.update(overrides)
    return {key: value for key, value in document.items() if value is not None}


def adapter_pin(world, **pin):
    return [{"codeRepository": world.url("adapter"), **pin}]


# ---------------------------------------------------------------------------
# The cases. Each builds its world and returns the directory under test.
# ---------------------------------------------------------------------------


def engine_on_main(world):
    engine = world.clone("engine")
    write_file(engine, engine_file(world, adapter_pin(world, branch="main")))
    return engine


def adapter_naming_engine(world):
    adapter = world.clone("adapter")
    write_file(adapter, {
        "testedWith": [{"codeRepository": world.url("engine"), "branch": "main"}]
    })
    return adapter


def two_pin_kinds(world):
    engine = world.clone("engine")
    write_file(engine, engine_file(world, adapter_pin(world, branch="main", tag="v1")))
    return engine


def engine_without_command(world):
    engine = world.clone("engine")
    write_file(engine, engine_file(world, adapter_pin(world, branch="main"), command=None))
    return engine


def adapter_carrying_specification(world):
    adapter = adapter_naming_engine(world)
    document = json.loads((adapter / "compatibility.json").read_text(encoding="utf-8"))
    document["specification"] = engine_file(world, [])["specification"]
    write_file(adapter, {k: v for k, v in document.items() if k != "@context"})
    return adapter


def engine_form_in_adapter(world):
    adapter = world.clone("adapter")
    write_file(adapter, engine_file(world, []))
    return adapter


def misspelt_key(world):
    engine = engine_on_main(world)
    document = json.loads((engine / "compatibility.json").read_text(encoding="utf-8"))
    document["testedwith"] = document.pop("testedWith")
    write_file(engine, {k: v for k, v in document.items() if k != "@context"})
    return engine


def string_vector(world):
    engine = world.clone("engine")
    write_file(engine, engine_file(world, [], setup="npm ci"))
    return engine


def dirty_sibling(world):
    engine = engine_on_main(world)
    adapter = world.clone("adapter")
    (adapter / "README.md").write_text("an uncommitted edit\n", encoding="utf-8")
    return engine


def unreachable(world):
    engine = world.clone("engine")
    write_file(engine, engine_file(world, [{
        "codeRepository": (world.origins / "renamed-away").as_uri(),
        "tag": "v1",
    }]))
    return engine


def feature_branch(world):
    engine = world.clone("engine")
    write_file(engine, engine_file(world, adapter_pin(world, branch="feat/next")))
    return engine


def commit_off_main(world):
    engine = world.clone("engine")
    write_file(engine, engine_file(
        world, adapter_pin(world, commit=world.commits["adapter feat/next"])
    ))
    return engine


def tag_on_main(world):
    engine = world.clone("engine")
    write_file(engine, engine_file(world, adapter_pin(world, tag="v1")))
    return engine


VALIDATE_ERROR = (
    "A compatibility.json is an engine's, carrying exactly one specification, "
    "one setup and one command, or an adapter's, carrying none of the three."
)

CASES = [
    {
        "name": "validate: an engine's file",
        "build": engine_on_main,
        "steps": [("validate", 0)],
        "expect": ["the form is an engine's, as the directory is", "PASS"],
    },
    {
        "name": "validate: an adapter's file",
        "build": adapter_naming_engine,
        "steps": [("validate", 0)],
        "expect": ["the form is an adapter's, as the directory is", "PASS"],
    },
    {
        "name": "validate: an adapter with no compatibility.json",
        "build": lambda world: world.clone("adapter"),
        "steps": [("validate", 0)],
        "expect": ["has no compatibility.json: nothing to check", "validate: nothing to check"],
    },
    {
        "name": "validate: two pin kinds in one entry",
        "build": two_pin_kinds,
        "steps": [("validate", 1)],
        "expect": ["A pin names exactly one of commit, tag or branch."],
    },
    {
        "name": "validate: an engine's file without command",
        "build": engine_without_command,
        "steps": [("validate", 1)],
        "expect": [VALIDATE_ERROR],
    },
    {
        "name": "validate: an adapter's file carrying specification",
        "build": adapter_carrying_specification,
        "steps": [("validate", 1)],
        "expect": [VALIDATE_ERROR],
    },
    {
        "name": "validate: an engine's form in an adapter's directory",
        "build": engine_form_in_adapter,
        "steps": [("validate", 1)],
        "expect": [
            "so it is an adapter, and an adapter's compatibility.json carries "
            "no specification, setup, command"
        ],
    },
    {
        "name": "validate: a key the context does not define",
        "build": misspelt_key,
        "steps": [("validate", 1)],
        "expect": ["testedwith is not a key the context defines"],
    },
    {
        "name": "validate: an argument vector written as a string",
        "build": string_vector,
        "steps": [("validate", 1)],
        "expect": ["setup is an argument vector, written as a JSON array of strings"],
    },
    {
        "name": "resolve: a branch pin uses the sibling's uncommitted edits, flagged",
        "build": dirty_sibling,
        "steps": [("resolve", 0)],
        "expect": [
            "branch main is {adapter} (the sibling's working tree, with uncommitted edits)",
            "a result produced from uncommitted edits is feedback, never evidence",
        ],
    },
    {
        "name": "resolve: a counterpart that cannot be reached",
        "build": unreachable,
        "steps": [("resolve", 1)],
        "expect": ["renamed-away could not be reached: it may be private, renamed or deleted"],
        "forbid": ["Traceback"],
    },
    {
        "name": "ready: a pin to a feature branch",
        "build": feature_branch,
        "steps": [("ready", 1)],
        "expect": ["branch feat/next: not the default branch, main"],
    },
    {
        "name": "ready: a commit not on the default branch",
        "build": commit_off_main,
        "steps": [("ready", 1)],
        "expect": ["{adapter feat/next} is not on main, the default branch"],
    },
    {
        "name": "ready: a tag on the default branch, and the spec pin",
        "build": tag_on_main,
        "steps": [("ready", 0)],
        "expect": [
            "testedWith: {url adapter} tag v1: {adapter} is on main",
            "specification: {url specification} commit {specification}: "
            "{specification} is on main",
        ],
    },
    {
        "name": "ready: a pin to the default branch",
        "build": engine_on_main,
        "steps": [("ready", 0)],
        "expect": ["branch main: the default branch"],
    },
]


# ---------------------------------------------------------------------------


def fill(fragment, world):
    """A fragment with the world's commits and URLs put in."""
    for name, commit in world.commits.items():
        fragment = fragment.replace("{" + name + "}", commit)
    for name in ("adapter", "engine", "specification"):
        fragment = fragment.replace("{url " + name + "}", world.url(name))
    return fragment


def run_case(case):
    failures = []
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
        world = World(directory)
        subject = case["build"](world)
        temporary = world.root / "tmp"
        temporary.mkdir()
        env = dict(os.environ, TMPDIR=str(temporary), TEMP=str(temporary), TMP=str(temporary))
        env.pop("CI", None)

        output = ""
        for step, expected in case["steps"]:
            run = subprocess.run(
                [sys.executable, str(TOOL), step, str(subject), "--mode", case.get("mode", "local")],
                capture_output=True,
                text=True,
                env=env,
            )
            output += run.stdout + run.stderr
            if run.returncode != expected:
                failures.append(f"{step} exited {run.returncode}, {expected} expected")

        for fragment in case["expect"]:
            if fill(fragment, world) not in output:
                failures.append(f"the run does not say: {fill(fragment, world)}")
        for fragment in case.get("forbid", ()):
            if fill(fragment, world) in output:
                failures.append(f"the run says what it must not: {fill(fragment, world)}")
        if "check" in case:
            failures += case["check"](world, subject, temporary)

        if failures:
            print(output)
    return failures


def main():
    print(f"Tool:    {TOOL}")
    print(f"Subject: {ADAPTER}, and throwaway repositories beside it")
    print()

    failed = 0
    for case in CASES:
        failures = run_case(case)
        if failures:
            failed += 1
            print(f"  FAIL  {case['name']}")
            for failure in failures:
                print(f"        {failure}")
        else:
            print(f"  ok    {case['name']}")

    print()
    print(f"{len(CASES)} case(s): {len(CASES) - failed} as specified, {failed} not")
    print("PASS" if not failed else "FAIL")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
