#!/usr/bin/env python3
"""Usage:

    python3 scripts/compatibility.py validate <dir>
    python3 scripts/compatibility.py resolve  <dir> [--mode ci|local] [--results <dir>]
    python3 scripts/compatibility.py checkout <dir> [--mode ci|local] [--results <dir>]
    python3 scripts/compatibility.py run      <dir> [--results <dir>]
    python3 scripts/compatibility.py judge   [<dir>] [--results <dir>]
    python3 scripts/compatibility.py ready    <dir>
    python3 scripts/compatibility.py spec-pin <dir> [--output <file>]

Exit status is 1 when the subcommand fails or did not run, 0 otherwise.
Requires git; validate also needs pyshacl and rdflib, and judge rdflib.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

SPEC_ROOT = Path(__file__).resolve().parent.parent
SHAPES = SPEC_ROOT / "shapes" / "bridge.shapes.ttl"
CONTEXT_FILE = SPEC_ROOT / "vocab" / "compatibility.context.jsonld"

CONTEXT_IRI = "https://ns.cascadeprotocol.org/bridge/v1-draft/compatibility.jsonld"

FILE = "compatibility.json"
CRATE = "ro-crate-metadata.json"

ENGINE_KEYS = ("specPin", "setup", "command")
TOP_KEYS = {"@context", "mustPassWith", *ENGINE_KEYS}
PIN_KINDS = ("commit", "tag", "branch")
PIN_KEYS = {"codeRepository", *PIN_KINDS}
SHA = re.compile(r"^[0-9a-f]{40}$")

OK = "ok"
FAIL = "FAIL"
NOT_RUN = "not run"
NONE = "nothing to check"


class Stop(Exception):
    pass


def report(ok, line):
    print(("  ok    " if ok else "  FAIL  ") + line)


def note(line):
    print("  note  " + line)


def warn(line):
    print("  warn  " + line)


def git(*args, cwd=None):
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


def unreachable(url, run):
    return Stop(
        f"{url} could not be reached: it may be private, renamed or deleted, "
        f"or the network refused (git: {first_line(run.stderr)})"
    )


def is_adapter(directory):
    return (directory / CRATE).is_file()


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise Stop(f"{path} is not JSON: {error}") from error


def read_file(directory):
    path = directory / FILE
    return read_json(path) if path.is_file() else None


def repository_name(url):
    name = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
    return name[: -len(".git")] if name.endswith(".git") else name


def name_clashes(directory, document):
    listed = document.get("mustPassWith")
    urls = [
        pin["codeRepository"]
        for pin in (listed if isinstance(listed, list) else [])
        if isinstance(pin, dict) and isinstance(pin.get("codeRepository"), str)
    ]
    problems = []
    seen = {}
    for url in urls:
        name = repository_name(url)
        if name.casefold() in seen:
            problems.append(
                "Each repository name appears in mustPassWith at most once, "
                f"compared without case: {seen[name.casefold()]} and {url} "
                f"would both be checked out at ../{name}"
            )
        seen[name.casefold()] = url
    reserved = {
        "cascade-bridge-spec": "that is where the starter checks the "
        "specification out beside this repository",
        directory.resolve().name.casefold(): "that is this repository's own "
        "directory",
    }
    for url in urls:
        name = repository_name(url)
        if name.casefold() in reserved:
            problems.append(
                f"No repository in mustPassWith is named {name}, compared "
                f"without case: {reserved[name.casefold()]}"
            )
    return problems


class Pin:
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
    if not isinstance(entry, dict):
        raise Stop(f"{label} is not a pin; run validate first")
    kinds = [kind for kind in PIN_KINDS if kind in entry]
    if not isinstance(entry.get("codeRepository"), str) or len(kinds) != 1:
        raise Stop(f"{label} is not a pin; run validate first")
    return Pin(label, entry["codeRepository"], kinds[0], entry[kinds[0]])


def entries(document):
    return [
        pin_from("mustPassWith", entry)
        for entry in (document or {}).get("mustPassWith", [])
    ]


def spec_pin(directory, document):
    if not is_adapter(directory):
        if not document or "specPin" not in document:
            raise Stop(
                f"{directory} holds no {CRATE}, so it is an engine, and an "
                f"engine states its spec pin as specPin in {FILE}"
            )
        return pin_from("specPin", document["specPin"])
    crate = read_json(directory / CRATE)
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


def problems_json_ld_hides_from_shacl(document):
    problems = [f"{key} is not a key the context defines" for key in document if key not in TOP_KEYS]
    for key in ("setup", "command"):
        if key in document and not isinstance(document[key], list):
            problems.append(f"{key} is an argument vector, written as a JSON array of strings")
    if "mustPassWith" in document and not isinstance(document["mustPassWith"], list):
        problems.append("mustPassWith is a list of pins, written as a JSON array, even of one")
    if "specPin" in document and not isinstance(document["specPin"], dict):
        problems.append("specPin is one pin, written as a JSON object")
    pins = []
    for label in ("specPin", "mustPassWith"):
        value = document.get(label)
        pins += [(label, pin) for pin in (value if isinstance(value, list) else [value])]
    for label, pin in pins:
        if isinstance(pin, dict):
            problems += [
                f"{key}, in {label}, is not a key the context defines"
                for key in pin
                if key not in PIN_KEYS
            ]
    return problems


def conform(directory, document):
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
        advanced=True,
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

    problems = problems_json_ld_hides_from_shacl(document) + name_clashes(directory, document)
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
            f"{FILE} carries specPin, setup and command",
        )
    elif conforms:
        report(True, f"the form is {kind}'s, as the directory is")

    listed = document.get("mustPassWith")
    count = len(listed) if isinstance(listed, list) else 0
    if not problems and conforms:
        note(f"{count} mustPassWith entr{'y' if count == 1 else 'ies'}")
    return OK if conforms and not problems else FAIL


def ls_remote(url, *patterns):
    run = git("ls-remote", url, *patterns)
    if run.returncode != 0:
        raise unreachable(url, run)
    refs = {}
    for line in run.stdout.splitlines():
        sha, _, ref = line.partition("\t")
        refs[ref] = sha
    return refs


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
            return line[len("ref: refs/heads/"):].split("\t", 1)[0]
    raise Stop(f"{url} names no default branch")


def sibling(directory, pin):
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
        resolved.update(commit=remote_tag_commit(pin.repository, pin.value), source="the tag")
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
            "evidence"
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
                "fetch", "--quiet", "--filter=blob:none", url,
                f"+refs/heads/{branch}:refs/heads/{branch}",
                cwd=repository,
            )
            if run.returncode != 0:
                raise unreachable(url, run)
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
            commit = pin.value if pin.kind == "commit" else remote_tag_commit(pin.repository, pin.value)
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


def local_checkout(directory, resolved):
    pin = Pin(resolved["label"], resolved["codeRepository"], resolved["kind"], resolved["value"])
    path = sibling(directory, pin)
    if resolved["source"] == "the sibling's working tree":
        return path
    commit = resolved["commit"]
    if local_commit(path, commit) is None:
        raise Stop(
            f"the sibling at {path} does not hold {commit}; fetch it, with "
            f"git -C {path} fetch --all --tags, and run again"
        )
    tree = Path(tempfile.gettempdir()) / "cascade-compatibility" / "worktrees" / f"{pin.name}-{commit[:12]}"
    if tree.exists():
        if local_commit(tree, "HEAD") == commit:
            return tree
        git("worktree", "remove", "--force", str(tree), cwd=path)
        shutil.rmtree(tree, ignore_errors=True)
        git("worktree", "prune", cwd=path)
    tree.parent.mkdir(parents=True, exist_ok=True)
    run = git("worktree", "add", "--detach", "--quiet", str(tree), commit, cwd=path)
    if run.returncode != 0:
        raise Stop(f"git made no worktree of {path} at {commit}: {first_line(run.stderr)}")
    return tree


def ci_checkout(directory, resolved):
    path = directory.parent / resolved["name"]
    commit = resolved["commit"]
    if path.exists():
        if local_commit(path, "HEAD") == commit:
            return path
        raise Stop(f"{path} is already there, and is not {resolved['codeRepository']} at {commit}")
    run = git(
        "clone", "--quiet", "--no-checkout", "--filter=blob:none",
        resolved["codeRepository"], str(path),
    )
    if run.returncode != 0:
        raise unreachable(resolved["codeRepository"], run)
    run = git("checkout", "--quiet", "--detach", commit, cwd=path)
    if run.returncode != 0:
        raise Stop(f"{resolved['codeRepository']} does not hold {commit}: {first_line(run.stderr)}")
    return path


def cmd_checkout(directory, args):
    print(f"Counterparts, checked out in {args.mode} mode beside {directory.name}")
    results = results_directory(directory, args)
    record = {"directory": str(directory), "mode": args.mode, "pins": [], "checkedOut": False}
    write_record(results, record)
    pins = entries(read_file(directory))
    resolved, ok = resolve_all(directory, args, pins)
    record["pins"] = resolved
    if ok:
        place = ci_checkout if args.mode == "ci" else local_checkout
        for entry in resolved:
            entry["path"] = str(place(directory, entry))
            report(True, f"{entry['codeRepository']} is at {entry['path']}")
        record["checkedOut"] = True
    write_record(results, record)
    if not pins:
        report(True, f"{directory} lists no counterpart: nothing to check")
        return NONE
    note(f"recorded in {results / 'record.json'}")
    return OK if ok else FAIL


def executable(argv, cwd):
    first = argv[0]
    if "/" in first or "\\" in first:
        candidate = Path(cwd, first)
        return [str(candidate) if candidate.exists() else first, *argv[1:]]
    return [shutil.which(first) or first, *argv[1:]]  # so Windows finds npm.cmd


def execute(argv, cwd):
    try:
        run = subprocess.run(
            executable(argv, cwd), cwd=cwd, capture_output=True,
            encoding="utf-8", errors="replace",
        )
    except OSError as error:
        report(False, f"{argv[0]} could not be started in {cwd}: {error}")
        return None
    for line in (run.stdout + run.stderr).splitlines():
        print(f"        | {line}")
    return run.returncode


def vectors(engine):
    document = read_file(engine) or {}
    setup, command = document.get("setup"), document.get("command")
    if isinstance(setup, list) and setup and isinstance(command, list) and command:
        return setup, command
    return None


def cmd_run(directory, args):
    results = results_directory(directory, args)
    record = read_record(results)
    if not record.get("checkedOut"):
        raise Stop("the record holds no checkout: run checkout first")
    reports = results / "earl"
    shutil.rmtree(reports, ignore_errors=True)
    reports.mkdir(parents=True)
    pins = [entry for entry in record["pins"] if entry["label"] == "mustPassWith"]
    print("Each engine on each adapter")
    if not pins:
        report(True, "no counterpart to run: nothing to check")
        return NONE

    adapter_side = is_adapter(directory)
    set_up = {}
    not_run = 0
    for entry in pins:
        counterpart = Path(entry["path"])
        engine, adapter = (counterpart, directory) if adapter_side else (directory, counterpart)
        entry["adapter"] = str(adapter)
        found = vectors(engine)
        if found is None:
            not_run += 1
            report(False, f"{engine} states no setup and command, so {entry['name']} was not run")
            continue
        setup, command = found
        if engine not in set_up:
            print(f"  setup {' '.join(setup)}   (in {engine})")
            set_up[engine] = execute(setup, engine) == 0
            if not set_up[engine]:
                report(False, f"the setup failed in {engine}")
        if not set_up[engine]:
            not_run += 1
            report(False, f"{entry['name']} was not run: its engine's setup failed")
            continue
        earl = str(reports / f"{entry['name']}.ttl")
        argv = [*command, "test", str(adapter), "--earl", earl]
        print(f"  run   {' '.join(argv)}   (in {engine})")
        status = execute(argv, engine)
        if status is None:
            not_run += 1
            continue
        entry["report"] = earl
        wrote = Path(earl).is_file()
        report(
            True,
            f"{entry['name']} ran, exit status {status}, which nothing relies on; "
            + ("its report is " + earl if wrote else "it wrote no report"),
        )
    write_record(results, record)
    return NOT_RUN if not_run else OK


EARL = "http://www.w3.org/ns/earl#"
MF = "http://www.w3.org/2001/sw/DataAccess/tests/test-manifest#"
OUTCOMES = {"passed", "failed", "cantTell", "inapplicable", "untested"}
NOT_HOLDING = {"failed", "inapplicable"}


def manifest_entries_relative_to_adapter(adapter):
    from rdflib import Graph, URIRef

    adapter = adapter.resolve()
    crate = read_json(adapter / CRATE)
    nodes = {node.get("@id"): node for node in crate.get("@graph", [])}
    named = (nodes.get("./") or {}).get("bridge:testManifest")
    if not isinstance(named, dict) or not named.get("@id"):
        raise Stop(f"{adapter / CRATE} names no bridge:testManifest")
    path = adapter / named["@id"]
    graph = Graph().parse(path, format="turtle", publicID=path.as_uri())
    listed = graph.value(URIRef(path.as_uri()), URIRef(MF + "entries"))
    root = adapter.as_uri() + "/"
    return [str(entry).removeprefix(root) for entry in graph.items(listed)] if listed else []


def judge_report(path, adapter):
    from rdflib import Graph, URIRef

    if not path.is_file():
        return False, "it wrote no report"
    try:
        graph = Graph().parse(path, format="turtle")
    except Exception as error:
        return False, f"its report does not parse as Turtle: {first_line(str(error))}"
    tally = {}
    for outcome in graph.objects(None, URIRef(EARL + "outcome")):
        name = str(outcome).removeprefix(EARL)
        tally[name] = tally.get(name, 0) + 1
    if not tally:
        return False, "its report records no outcome"
    unknown = sorted(name for name in tally if name not in OUTCOMES)
    said = ", ".join(f"{count} {name}" for name, count in sorted(tally.items()))
    if unknown:
        said += f"; {', '.join(unknown)} is not one of EARL's five outcomes"

    try:
        expected = manifest_entries_relative_to_adapter(adapter)
    except Exception as error:
        return False, f"{said}; the adapter's test manifest could not be read: {first_line(str(error))}"
    tested = set()
    for assertion, result in graph.subject_objects(URIRef(EARL + "result")):
        if graph.value(result, URIRef(EARL + "outcome")) is not None:
            tested.update(str(test) for test in graph.objects(assertion, URIRef(EARL + "test")))
    missing = [
        entry for entry in expected
        if not any(test == entry or test.endswith("/" + entry) for test in tested)
    ]
    if missing:
        said += (
            f"; {len(missing)} of the manifest's {len(expected)} tests have no outcome: "
            + ", ".join(entry.rsplit("#", 1)[-1] for entry in missing)
        )
    else:
        said += f", covering all {len(expected)} of the manifest's tests"
    return not unknown and not missing and not (NOT_HOLDING & tally.keys()), said


def cmd_judge(directory, args):
    results = results_directory(directory, args)
    record = read_record(results)
    if not record.get("checkedOut"):
        raise Stop("the record holds no checkout: run checkout first")
    pins = [entry for entry in record["pins"] if entry["label"] == "mustPassWith"]
    print("Each entry, judged by its EARL report")
    if not pins:
        report(True, "no entry: nothing to check")
        return NONE
    held = 0
    for entry in pins:
        if "report" in entry:
            holds, said = judge_report(Path(entry["report"]), Path(entry["adapter"]))
        else:
            holds, said = False, "it was not run"
        held += holds
        flag = ", with uncommitted edits" if entry["uncommittedEdits"] else ""
        report(
            holds,
            f"{entry['codeRepository']} at {entry['commit']} ({entry['kind']} "
            f"{entry['value']}{flag}): {'holds' if holds else 'does not hold'}; {said}",
        )
    if any(entry["uncommittedEdits"] for entry in pins):
        note("a result produced from uncommitted edits is feedback, never evidence")
    print(f"  {len(pins)} entr{'y' if len(pins) == 1 else 'ies'}: {held} hold, {len(pins) - held} do not")
    return OK if held == len(pins) else FAIL


def cmd_spec_pin(directory, args):
    print("The specification pin")
    pin = spec_pin(directory, read_file(directory))
    report(True, str(pin))
    if args.output:
        with open(args.output, "a", encoding="utf-8") as handle:
            handle.write(f"repository={pin.repository}\nkind={pin.kind}\nref={pin.value}\n")
    return OK


COMMANDS = {
    "spec-pin": cmd_spec_pin,
    "validate": cmd_validate,
    "resolve": cmd_resolve,
    "checkout": cmd_checkout,
    "run": cmd_run,
    "judge": cmd_judge,
    "ready": cmd_ready,
}


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("command", choices=sorted(COMMANDS))
    parser.add_argument(
        "directory", type=Path, nargs="?", default=Path("."),
        help="the repository under test; the current directory when omitted",
    )
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
    parser.add_argument(
        "--output",
        default=None,
        help="spec-pin only: a file to append repository=, kind= and ref= to",
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
    print("PASS" if status == OK else NONE if status == NONE else "FAIL")
    return 1 if status in (FAIL, NOT_RUN) else 0


if __name__ == "__main__":
    sys.exit(main())
