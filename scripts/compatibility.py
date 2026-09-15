#!/usr/bin/env python3
"""Check the entries of a compatibility.json, locally and in CI.

compatibility.md is the contract; this is the one tool that implements it. Every
subcommand takes the directory of the repository under test and reads the files
in it. It names no adapter and no engine, and learns every counterpart from the
file it is handed: a specification that knew which adapters or engines exist is
the bug pinning.md is written against.

    validate <dir>   the file conforms to the shapes, in the form its directory
                     needs: an adapter's, when the directory holds
                     ro-crate-metadata.json, and an engine's when it does not
    resolve <dir>    every pin resolves to a commit, printed and recorded
    ready <dir>      the merge-time rule: every pin names the counterpart's
                     default branch, or a commit or tag on it

**Every subcommand says whether it checked anything.** It reports in the words
adapter/validation.md fixes -- ok, FAIL, nothing to check, not run -- and a
repository with no compatibility.json has nothing to check, which is not a pass.

Pins are resolved where compatibility.md says. In CI (--mode ci, the default
when the CI variable is "true"), a branch is its tip on the counterpart. Locally
(--mode local), a branch is the sibling clone's working tree when the sibling is
on that branch, and a result produced from its uncommitted edits is recorded as
such: feedback, never evidence. The record is written under --results, by
default a directory named for the repository under the system temporary
directory, so that the subcommands after resolve read what it resolved rather
than resolving again.

A counterpart that cannot be reached stops the run with a message naming it,
and a missing sibling stops it with the git clone command that fixes it.
Nothing is cloned into a developer's directory unasked.

Usage:

    python3 scripts/compatibility.py validate <dir>
    python3 scripts/compatibility.py resolve <dir> [--mode ci|local] [--results <dir>]
    python3 scripts/compatibility.py ready <dir>

Exit status is 0 when the subcommand passes and 1 when it fails.

Requires git. validate also needs pyshacl and rdflib (pip install pyshacl
rdflib), imported only there, so that the rest runs on a bare interpreter.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

SPEC_ROOT = Path(__file__).resolve().parent.parent
SHAPES = SPEC_ROOT / "shapes" / "bridge.shapes.ttl"
CONTEXT_FILE = SPEC_ROOT / "vocab" / "compatibility.context.jsonld"

# The IRI a compatibility.json names as its @context. It does not dereference
# yet, so the file above is read in its place; a file naming any other context
# is not one this tool can read, and is refused rather than fetched.
CONTEXT_IRI = "https://ns.cascadeprotocol.org/bridge/v1-draft/compatibility.jsonld"

FILE = "compatibility.json"
CRATE = "ro-crate-metadata.json"

ENGINE_KEYS = ("specification", "setup", "command")
TOP_KEYS = {"@context", "testedWith", *ENGINE_KEYS}
PIN_KINDS = ("commit", "tag", "branch")
PIN_KEYS = {"codeRepository", *PIN_KINDS}
SHA = re.compile(r"^[0-9a-f]{40}$")

OK = "ok"
FAIL = "FAIL"
NOT_RUN = "not run"
NONE = "nothing to check"


class Stop(Exception):
    """A condition that ends the run: said in a sentence, never a traceback."""


def report(ok, line):
    print(("  ok    " if ok else "  FAIL  ") + line)


def note(line):
    print("  note  " + line)


def warn(line):
    print("  warn  " + line)


def git(*args, cwd=None):
    """git, never prompting: a prompt in CI hangs, and locally it hides the
    unreachable-counterpart message behind a credential dialog."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def first_line(text):
    return next((line.strip() for line in text.splitlines() if line.strip()), "")


# ============================================================================
# The repository under test, and its pins
# ============================================================================


def is_adapter(directory):
    """An adapter is a directory holding a crate; an engine has none
    (compatibility.md). The same test the adapter lint begins with."""
    return (directory / CRATE).is_file()


def read_file(directory):
    """compatibility.json as JSON, or None when the directory has none."""
    path = directory / FILE
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise Stop(f"{path} is not JSON: {error}") from error


def repository_name(url):
    """The directory a counterpart's clone sits in: the last segment of its
    URL, without .git, which is its repository's name (compatibility.md)."""
    name = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
    return name[: -len(".git")] if name.endswith(".git") else name


class Pin:
    """A repository at a revision, and where the pin was read."""

    def __init__(self, label, repository, kind, value):
        self.label = label
        self.repository = repository
        self.kind = kind
        self.value = value

    @property
    def name(self):
        return repository_name(self.repository)

    def __str__(self):
        return f"{self.label}: {self.repository} {self.kind} {self.value}"


def pin_from(label, entry):
    kinds = [kind for kind in PIN_KINDS if kind in entry]
    if not isinstance(entry.get("codeRepository"), str) or len(kinds) != 1:
        raise Stop(f"{label} is not a pin; run validate first")
    return Pin(label, entry["codeRepository"], kinds[0], entry[kinds[0]])


def entries(document):
    return [
        pin_from("testedWith", entry)
        for entry in (document or {}).get("testedWith", [])
    ]


def spec_pin(directory, document):
    """The one pin every repository carries.

    An adapter's is the crate's bridge:specPin. The crate is read as JSON rather
    than JSON-LD, so that reading a pin needs no RO-Crate context from the
    network; the lint's check 2 is what holds the crate to its shape. An
    engine's is the specification in its compatibility.json.
    """
    if not is_adapter(directory):
        if not document or "specification" not in document:
            raise Stop(
                f"{directory} holds no {CRATE}, so it is an engine, and an "
                f"engine states its spec pin as specification in {FILE}"
            )
        return pin_from("specification", document["specification"])
    crate = json.loads((directory / CRATE).read_text(encoding="utf-8"))
    nodes = {node.get("@id"): node for node in crate.get("@graph", [])}
    pin = (nodes.get("./") or {}).get("bridge:specPin")
    entity = nodes.get(pin.get("@id")) if isinstance(pin, dict) else None
    if not entity:
        raise Stop(f"{directory / CRATE} names no bridge:specPin entity")
    repository = entity.get("codeRepository")
    if isinstance(repository, dict):
        repository = repository.get("@id")
    if not repository or not entity.get("version"):
        raise Stop(
            f"the crate's bridge:specPin, {pin['@id']}, carries no "
            "codeRepository and version to pin"
        )
    return Pin("bridge:specPin", repository, "commit", entity["version"])


# ============================================================================
# validate
# ============================================================================


def unknown_keys(document):
    """Keys the context does not define, and argument vectors not written as
    arrays. JSON-LD drops the first silently and turns the second into a
    one-element list, so SHACL never sees either: a misspelt testedWith would
    be a file asserting nothing, and "npm ci" would be one argument, run
    without a shell."""
    problems = [f"{key} is not a key the context defines" for key in document if key not in TOP_KEYS]
    for key in ("setup", "command"):
        if key in document and not isinstance(document[key], list):
            problems.append(f"{key} is an argument vector, written as a JSON array of strings")
    pins = [("specification", document.get("specification"))]
    pins += [("testedWith", entry) for entry in document.get("testedWith") or []]
    for label, pin in pins:
        if isinstance(pin, dict):
            problems += [
                f"{key}, in {label}, is not a key the context defines"
                for key in pin
                if key not in PIN_KEYS
            ]
    return problems


def conform(directory, document):
    """SHACL, with this repository's context read in place of its IRI."""
    from pyshacl import validate as shacl_validate
    from rdflib import Graph
    from rdflib.namespace import RDF, SH

    context = json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))["@context"]
    data = dict(document, **{"@context": context})
    graph = Graph().parse(
        data=json.dumps(data),
        format="json-ld",
        base=(directory / FILE).resolve().as_uri(),
    )
    conforms, results, _ = shacl_validate(
        graph,
        shacl_graph=Graph().parse(SHAPES, format="turtle"),
        advanced=True,  # the shapes use sh:sparql constraints
        inplace=False,
    )
    messages = sorted(
        {
            str(results.value(result, SH.resultMessage) or "").strip()
            for result in results.subjects(RDF.type, SH.ValidationResult)
        }
    )
    return conforms, messages


def cmd_validate(directory, _args):
    kind = "an adapter" if is_adapter(directory) else "an engine"
    print(f"{FILE}, in {kind}'s form")
    document = read_file(directory)
    if document is None:
        if is_adapter(directory):
            report(True, f"{directory} has no {FILE}: nothing to check")
            return NONE
        report(
            False,
            f"{directory} holds no {CRATE}, so it is an engine, and an engine "
            f"states its spec pin in {FILE}, which is not there",
        )
        return FAIL
    if not isinstance(document, dict) or document.get("@context") != CONTEXT_IRI:
        found = document.get("@context") if isinstance(document, dict) else document
        report(False, f"its @context is {found!r}, where a {FILE} names {CONTEXT_IRI}")
        return FAIL

    problems = unknown_keys(document)
    for problem in problems:
        report(False, problem)

    conforms, messages = conform(directory, document)
    if conforms:
        report(True, f"{SHAPES.name} against {FILE}")
    else:
        report(False, f"{len(messages)} shape violation(s)")
        for message in messages:
            print(f"        {message}")

    carried = [key for key in ENGINE_KEYS if key in document]
    if conforms and is_adapter(directory) and carried:
        problems.append("form")
        report(
            False,
            f"{directory} holds {CRATE}, so it is an adapter, and an adapter's "
            f"{FILE} carries no {', '.join(carried)}: its spec pin is the "
            "crate's bridge:specPin, and it is run rather than running anything",
        )
    elif conforms and not is_adapter(directory) and not carried:
        problems.append("form")
        report(
            False,
            f"{directory} holds no {CRATE}, so it is an engine, and an engine's "
            f"{FILE} carries specification, setup and command",
        )
    elif conforms:
        report(True, f"the form is {kind}'s, as the directory is")

    count = len(document.get("testedWith") or [])
    if not problems and conforms:
        note(f"{count} testedWith entr{'y' if count == 1 else 'ies'}")
    return OK if conforms and not problems else FAIL


# ============================================================================
# Resolving a pin
# ============================================================================


def ls_remote(url, *patterns):
    """Refs of a counterpart, by name. Unreachable is a stop, not a failure of
    one pin: nothing about the counterpart can be checked."""
    run = git("ls-remote", url, *patterns)
    if run.returncode != 0:
        raise Stop(
            f"{url} could not be reached: it may be private, renamed or "
            f"deleted, or the network refused (git: {first_line(run.stderr)})"
        )
    refs = {}
    for line in run.stdout.splitlines():
        sha, _, ref = line.partition("\t")
        refs[ref] = sha
    return refs


def remote_tag(url, tag):
    """The commit a tag names. An annotated tag's own object is listed first
    and the commit under ^{}; the commit is what a pin means."""
    refs = ls_remote(url, f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}")
    return refs.get(f"refs/tags/{tag}^{{}}") or refs.get(f"refs/tags/{tag}")


def remote_branch(url, branch):
    return ls_remote(url, f"refs/heads/{branch}").get(f"refs/heads/{branch}")


def default_branch(url):
    """Read from the counterpart, never assumed to be main."""
    run = git("ls-remote", "--symref", url, "HEAD")
    if run.returncode != 0:
        raise Stop(
            f"{url} could not be reached: it may be private, renamed or "
            f"deleted, or the network refused (git: {first_line(run.stderr)})"
        )
    for line in run.stdout.splitlines():
        if line.startswith("ref: refs/heads/"):
            return line[len("ref: refs/heads/"):].split("\t", 1)[0]
    raise Stop(f"{url} names no default branch")


def sibling(directory, pin):
    """The counterpart's clone beside the repository under test, or a stop
    with the command that puts it there."""
    path = directory.parent / pin.name
    if not (path / ".git").exists():
        raise Stop(
            f"{pin.repository} has no clone beside {directory.name}; "
            f"clone it with: git clone {pin.repository} {path}"
        )
    return path


def local_commit(path, ref):
    run = git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", cwd=path)
    return run.stdout.strip() if run.returncode == 0 else None


def resolve(directory, pin, mode):
    """What a pin names now, as a record entry. `commit` is None when it names
    nothing, which fails that pin and leaves the others to be resolved."""
    resolved = {
        "label": pin.label,
        "codeRepository": pin.repository,
        "name": pin.name,
        "kind": pin.kind,
        "value": pin.value,
        "commit": None,
        "source": None,
        "uncommittedEdits": False,
        "warning": None,
    }
    if pin.kind == "commit":
        resolved.update(commit=pin.value, source="the commit pinned")
    elif pin.kind == "tag":
        resolved.update(commit=remote_tag(pin.repository, pin.value), source="the tag")
    elif mode == "ci":
        resolved.update(
            commit=remote_branch(pin.repository, pin.value), source="the branch's tip"
        )
    else:
        path = sibling(directory, pin)
        current = git("symbolic-ref", "--quiet", "--short", "HEAD", cwd=path).stdout.strip()
        if current == pin.value:
            dirty = bool(git("status", "--porcelain", cwd=path).stdout.strip())
            resolved.update(
                commit=local_commit(path, "HEAD"),
                source="the sibling's working tree",
                uncommittedEdits=dirty,
            )
        else:
            commit = (
                local_commit(path, f"refs/heads/{pin.value}")
                or local_commit(path, f"refs/remotes/origin/{pin.value}")
                or remote_branch(pin.repository, pin.value)
            )
            resolved.update(
                commit=commit,
                source="the branch's last commit",
                warning=(
                    f"the sibling at {path} is on {current or 'a detached HEAD'}, "
                    f"not {pin.value}, so the branch's last commit is used"
                ),
            )
    return resolved


def describe(resolved):
    """One line naming the resolved commit and any uncommitted-edits flag."""
    flag = ", with uncommitted edits" if resolved["uncommittedEdits"] else ""
    return (
        f"{resolved['label']}: {resolved['codeRepository']} "
        f"{resolved['kind']} {resolved['value']} is {resolved['commit']} "
        f"({resolved['source']}{flag})"
    )


def results_directory(directory, args):
    if args.results:
        return Path(args.results).resolve()
    return Path(tempfile.gettempdir()) / "cascade-compatibility" / directory.name


def write_record(results, record):
    results.mkdir(parents=True, exist_ok=True)
    (results / "record.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )


def read_record(results):
    path = results / "record.json"
    if not path.is_file():
        raise Stop(f"{path} is not there: run resolve or checkout first")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_all(directory, args, pins):
    """Resolve and print each pin; the record's entries, and whether all
    resolved."""
    resolved_all, ok = [], True
    for pin in pins:
        resolved = resolve(directory, pin, args.mode)
        resolved_all.append(resolved)
        if resolved["commit"] is None:
            ok = False
            report(False, f"{pin}: names nothing in {pin.repository}")
            continue
        report(True, describe(resolved))
        if resolved["warning"]:
            warn(resolved["warning"])
    if any(resolved["uncommittedEdits"] for resolved in resolved_all):
        note(
            "a result produced from uncommitted edits is feedback, never "
            "evidence (compatibility.md)"
        )
    return resolved_all, ok


def cmd_resolve(directory, args):
    print(f"Pins, resolved in {args.mode} mode")
    document = read_file(directory)
    pins = [spec_pin(directory, document), *entries(document)]
    resolved, ok = resolve_all(directory, args, pins)
    results = results_directory(directory, args)
    write_record(
        results,
        {"directory": str(directory), "mode": args.mode, "pins": resolved},
    )
    note(f"recorded in {results / 'record.json'}")
    return OK if ok else FAIL


# ============================================================================
# ready
# ============================================================================


class Ancestry:
    """Whether a commit is on a counterpart's default branch.

    That branch is fetched without blobs into a scratch repository, once per
    counterpart, and asked with git merge-base --is-ancestor: the history is
    what is being asked about, and the files are not.
    """

    def __init__(self, scratch):
        self.scratch = Path(scratch)
        self.fetched = {}

    def on(self, url, branch, commit):
        repository = self.fetched.get(url)
        if repository is None:
            repository = self.scratch / f"counterpart-{len(self.fetched)}"
            git("init", "--quiet", "--bare", str(repository))
            run = git(
                "fetch", "--quiet", "--filter=blob:none", url,
                f"+refs/heads/{branch}:refs/heads/{branch}",
                cwd=repository,
            )
            if run.returncode != 0:
                raise Stop(
                    f"{url} could not be reached: it may be private, renamed "
                    f"or deleted, or the network refused (git: {first_line(run.stderr)})"
                )
            self.fetched[url] = repository
        run = git("merge-base", "--is-ancestor", commit, f"refs/heads/{branch}", cwd=repository)
        return run.returncode == 0


def cmd_ready(directory, _args):
    print("Every pin, at merge time")
    document = read_file(directory)
    pins = [spec_pin(directory, document), *entries(document)]
    failed = 0
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as scratch:
        ancestry = Ancestry(scratch)
        for pin in pins:
            branch = default_branch(pin.repository)
            if pin.kind == "branch":
                if pin.value == branch:
                    report(True, f"{pin}: the default branch")
                else:
                    failed += 1
                    report(
                        False,
                        f"{pin}: not the default branch, {branch}. A pull "
                        "request may pin a feature branch while both are open, "
                        "and cannot merge that way",
                    )
                continue
            commit = pin.value if pin.kind == "commit" else remote_tag(pin.repository, pin.value)
            if commit is None:
                failed += 1
                report(False, f"{pin}: names nothing in {pin.repository}")
            elif ancestry.on(pin.repository, branch, commit):
                report(True, f"{pin}: {commit} is on {branch}")
            else:
                failed += 1
                report(
                    False,
                    f"{pin}: {commit} is not on {branch}, the default branch. "
                    "Pin its merge commit once it has merged",
                )
    return FAIL if failed else OK


# ============================================================================

COMMANDS = {
    "validate": cmd_validate,
    "resolve": cmd_resolve,
    "ready": cmd_ready,
}


def main():
    parser = argparse.ArgumentParser(
        description="Check the entries of a compatibility.json against the "
        "Cascade Bridge Specification (compatibility.md)."
    )
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument("directory", type=Path, help="the repository under test")
    parser.add_argument(
        "--mode",
        choices=("ci", "local"),
        default="ci" if os.environ.get("CI") == "true" else "local",
        help="where pins resolve: ci, or local (siblings' working trees); "
        "ci when the CI variable is true",
    )
    parser.add_argument(
        "--results",
        default=None,
        help="where the record and the EARL reports go; by default a directory "
        "named for the repository under the system temporary directory",
    )
    args = parser.parse_args()
    directory = args.directory.resolve()
    if not directory.is_dir():
        print(f"  FAIL  {directory} is not a directory")
        return 1

    print(f"Repository: {directory}")
    print(f"Spec:       {SPEC_ROOT}")
    print()
    try:
        status = COMMANDS[args.command](directory, args)
    except Stop as stop:
        report(False, str(stop))
        status = FAIL
    print()
    print(f"{args.command}: {status}")
    print("FAIL" if status in (FAIL, NOT_RUN) else "PASS")
    return 1 if status in (FAIL, NOT_RUN) else 0


if __name__ == "__main__":
    sys.exit(main())
