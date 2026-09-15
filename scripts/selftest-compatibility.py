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
FAKE_ENGINE = SPEC_ROOT / "fixtures" / "fake-engine"
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
    engine         fixtures/fake-engine, with an engine's compatibility.json
                   committed beside it, so a checkout at any commit can run it
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

        def engine(path):
            shutil.copytree(FAKE_ENGINE, path, dirs_exist_ok=True)
            write_file(path, engine_file(self, []))

        self.publish("engine", engine)
        self.commits["engine"] = self.head("engine")

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


def engine_file(world, tested_with, canned="passed", **overrides):
    """An engine's compatibility.json, running the fake engine with the report
    `canned` names. The vectors name the running interpreter, so the case runs
    where python3 is not on PATH."""
    document = {
        "specification": {
            "codeRepository": world.url("specification"),
            "commit": world.commits["specification"],
        },
        "setup": [sys.executable, "-c", "pass"],
        "command": [sys.executable, "engine.py", "--canned", canned],
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


def tested_with_object(world):
    """One pin written as an object where the array goes, which JSON-LD reads
    as a one-element array and so gets past the shapes."""
    engine = world.clone("engine")
    write_file(engine, engine_file(world, adapter_pin(world, branch="main")[0]))
    return engine


def specification_array(world):
    engine = world.clone("engine")
    document = engine_file(world, [])
    write_file(engine, dict(document, specification=[document["specification"]]))
    return engine


def two_of_one_name(second):
    """Two counterparts whose clones would share one directory beside the
    repository under test: the adapter, and `second`'s URL."""
    def build(world):
        engine = world.clone("engine")
        write_file(engine, engine_file(world, [
            *adapter_pin(world, branch="main"),
            {"codeRepository": second(world), "branch": "main"},
        ]))
        return engine
    return build


def named_as_specification(world):
    engine = world.clone("engine")
    write_file(engine, engine_file(world, [{
        "codeRepository": (world.origins / "cascade-bridge-spec").as_uri(),
        "branch": "main",
    }]))
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


def engine_and_adapter(canned):
    """An engine on its adapter's default branch, the adapter's clone beside it."""
    def build(world):
        engine = world.clone("engine")
        write_file(engine, engine_file(world, adapter_pin(world, branch="main"), canned=canned))
        world.clone("adapter")
        return engine
    return build


def sibling_state(path):
    return (
        git("rev-parse", "HEAD", cwd=path),
        git("symbolic-ref", "--short", "HEAD", cwd=path),
        git("status", "--porcelain", cwd=path),
    )


def adapter_on_engine_commit(world):
    """The other direction: an adapter pinning its engine by commit, the
    engine's clone beside it on main with an edit of its own in flight."""
    adapter = world.clone("adapter")
    write_file(adapter, {
        "testedWith": [{"codeRepository": world.url("engine"), "commit": world.commits["engine"]}]
    })
    engine = world.clone("engine")
    (engine / "work-in-progress.txt").write_text("not committed\n", encoding="utf-8")
    world.before = sibling_state(engine)
    return adapter


def record_of(subject, temporary):
    path = temporary / "cascade-compatibility" / subject.name / "record.json"
    return json.loads(path.read_text(encoding="utf-8"))


def sibling_untouched(world, subject, temporary):
    failures = []
    if sibling_state(world.workspace / "engine") != world.before:
        failures.append("the sibling's working copy is not as it was")
    checkout = Path(record_of(subject, temporary)["pins"][0]["path"]).resolve()
    if temporary.resolve() not in checkout.parents:
        failures.append(f"the checkout is {checkout}, not a worktree under the temporary directory")
    return failures


def cloned_at_commit(world, subject, temporary):
    clone = world.workspace / "adapter"
    if not clone.is_dir():
        return ["nothing was cloned beside the repository under test"]
    head = git("rev-parse", "HEAD", cwd=clone)
    return [] if head == world.commits["adapter"] else [f"the clone is at {head}"]


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
        "forbid": ["\nPASS\n"],
    },
    {
        "name": "checkout: an engine listing no counterpart",
        "build": lambda world: world.clone("engine"),
        "steps": [("checkout", 0)],
        "expect": ["lists no counterpart: nothing to check", "checkout: nothing to check"],
        "forbid": ["\nPASS\n"],
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
        "name": "validate: testedWith written as one object",
        "build": tested_with_object,
        "steps": [("validate", 1)],
        "expect": ["testedWith is a list of pins, written as a JSON array"],
    },
    {
        "name": "validate: specification written as an array",
        "build": specification_array,
        "steps": [("validate", 1)],
        "expect": ["specification is one pin, written as a JSON object"],
    },
    {
        "name": "checkout: testedWith written as one object stops in a sentence",
        "build": tested_with_object,
        "steps": [("checkout", 1)],
        "expect": ["testedWith is not a pin; run validate first"],
        "forbid": ["Traceback"],
    },
    {
        "name": "validate: a fork of a counterpart, its name in another case",
        "build": two_of_one_name(lambda world: (world.origins / "fork" / "Adapter").as_uri()),
        "steps": [("validate", 1)],
        "expect": ["Each repository name appears in testedWith at most once"],
    },
    {
        "name": "validate: one counterpart with and without .git",
        "build": two_of_one_name(lambda world: world.url("adapter") + ".git"),
        "steps": [("validate", 1)],
        "expect": ["Each repository name appears in testedWith at most once"],
    },
    {
        "name": "validate: a counterpart named as the specification",
        "build": named_as_specification,
        "steps": [("validate", 1)],
        "expect": ["No repository in testedWith is named cascade-bridge-spec"],
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
    {
        "name": "spec-pin: an engine's specification",
        "build": engine_on_main,
        "steps": [("spec-pin", 0)],
        "expect": ["specification: {url specification} commit {specification}"],
    },
    {
        "name": "spec-pin: an adapter's bridge:specPin, read from its crate",
        "build": lambda world: world.clone("adapter"),
        "steps": [("spec-pin", 0)],
        "expect": ["bridge:specPin: https://github.com/jayostis/cascade-bridge-spec commit "],
    },
    {
        "name": "checkout, run, judge: an engine holding on its adapter's default branch",
        "build": engine_and_adapter("passed"),
        "steps": [("checkout", 0), ("run", 0), ("judge", 0)],
        "expect": [
            "fake engine: testing",
            "branch main): holds; 1 cantTell, 1 passed, 1 untested",
            "judge: ok",
        ],
        "forbid": ["does not hold"],
    },
    {
        "name": "judge: an entry that does not hold, from an engine that exits 0",
        "build": engine_and_adapter("failed"),
        "steps": [("checkout", 0), ("run", 0), ("judge", 1)],
        "expect": ["does not hold; 1 cantTell, 1 failed, 1 untested"],
    },
    {
        "name": "judge: a run that writes no report",
        "build": engine_and_adapter("none"),
        "steps": [("checkout", 0), ("run", 0), ("judge", 1)],
        "expect": ["it wrote no report", "does not hold; it wrote no report"],
    },
    {
        "name": "judge: a report that is not Turtle",
        "build": engine_and_adapter("garbled"),
        "steps": [("checkout", 0), ("run", 0), ("judge", 1)],
        "expect": ["does not hold; its report does not parse as Turtle"],
    },
    {
        "name": "judge: a report missing entries of the manifest, none failed",
        "build": engine_and_adapter("partial"),
        "steps": [("checkout", 0), ("run", 0), ("judge", 1)],
        "expect": [
            "does not hold; 1 passed; 2 of the manifest's 3 tests have no outcome: "
            "example-0002, example-release-2026-01"
        ],
    },
    {
        "name": "checkout: a missing sibling",
        "build": engine_on_main,
        "steps": [("checkout", 1)],
        "expect": ["has no clone beside engine; clone it with: git clone {url adapter}"],
        "forbid": ["Traceback"],
    },
    {
        "name": "judge: a branch pin on a sibling's uncommitted edits holds, flagged",
        "build": dirty_sibling,
        "steps": [("checkout", 0), ("run", 0), ("judge", 0)],
        "expect": [
            "(branch main, with uncommitted edits): holds",
            "a result produced from uncommitted edits is feedback, never evidence",
        ],
    },
    {
        "name": "checkout: a commit pin runs from a worktree, the sibling untouched",
        "build": adapter_on_engine_commit,
        "steps": [("checkout", 0), ("run", 0), ("judge", 0)],
        "expect": ["commit {engine} is {engine} (the commit pinned)", "holds"],
        "check": sibling_untouched,
    },
    {
        "name": "checkout: in CI, a clone at the resolved commit",
        "build": tag_on_main,
        "mode": "ci",
        "steps": [("checkout", 0), ("run", 0), ("judge", 0)],
        "expect": ["tag v1 is {adapter} (the tag)", "holds"],
        "check": cloned_at_commit,
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
