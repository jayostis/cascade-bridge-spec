import tempfile

from compatibility_tool import git
from compatibility_tool.console import Status, Stop, note, report, warn
from compatibility_tool.document import entries, read_file, spec_pin
from compatibility_tool.record import RECORD, Record, ResolvedPin, Source


def sibling(directory, pin):
    path = directory.parent / pin.name
    if not (path / ".git").exists():
        raise Stop(
            f"{pin.repository} has no clone beside {directory.name}; clone it with: git clone {pin.repository} {path}"
        )
    return path


def resolve(directory, pin, mode):
    if pin.kind == "commit":
        return ResolvedPin(pin, pin.value, Source.COMMIT)
    if pin.kind == "tag":
        return ResolvedPin(pin, git.remote_tag_commit(pin.repository, pin.value), Source.TAG)
    if mode == "ci":
        return ResolvedPin(pin, git.remote_branch(pin.repository, pin.value), Source.BRANCH_TIP)
    path = sibling(directory, pin)
    current = git.current_branch(path)
    if current == pin.value:
        return ResolvedPin(
            pin, git.local_commit(path, "HEAD"), Source.WORKING_TREE, uncommitted_edits=git.has_uncommitted_edits(path)
        )
    commit = (
        git.local_commit(path, f"refs/heads/{pin.value}")
        or git.local_commit(path, f"refs/remotes/origin/{pin.value}")
        or git.remote_branch(pin.repository, pin.value)
    )
    warning = f"the sibling at {path} is on {current or 'a detached HEAD'}, not {pin.value}, so the branch's last commit is used"
    return ResolvedPin(pin, commit, Source.BRANCH_LAST_COMMIT, warning=warning)


def resolve_and_report(directory, pins, mode):
    resolved = []
    for pin in pins:
        entry = resolve(directory, pin, mode)
        resolved.append(entry)
        if entry.commit is None:
            report(False, f"{pin}: names nothing in {pin.repository}")
            continue
        report(True, entry.describe())
        if entry.warning:
            warn(entry.warning)
    if any(entry.uncommitted_edits for entry in resolved):
        note("a result produced from uncommitted edits is feedback, never evidence")
    return resolved, all(entry.commit is not None for entry in resolved)


def place_locally(directory, entry, worktrees):
    path = sibling(directory, entry.pin)
    if entry.source is Source.WORKING_TREE:
        return path
    if git.local_commit(path, entry.commit) is None:
        raise Stop(
            f"the sibling at {path} does not hold {entry.commit}; fetch it, with "
            f"git -C {path} fetch --all --tags, and run again"
        )
    return git.worktree_at(path, worktrees / f"{entry.pin.name}-{entry.commit[:12]}", entry.commit)


def place_in_ci(directory, entry):
    path = directory.parent / entry.pin.name
    if not path.exists():
        return git.clone_at(entry.pin.repository, path, entry.commit)
    if git.local_commit(path, "HEAD") == entry.commit:
        return path
    raise Stop(f"{path} is already there, and is not {entry.pin.repository} at {entry.commit}")


def resolve_command(directory, options):
    print(f"Pins, resolved in {options.mode} mode")
    document = read_file(directory)
    pins = [spec_pin(directory, document), *entries(document)]
    resolved, ok = resolve_and_report(directory, pins, options.mode)
    Record(directory, options.mode, resolved).save(options.results)
    note(f"recorded in {options.results / RECORD}")
    return Status.OK if ok else Status.FAIL


def checkout_command(directory, options):
    print(f"Counterparts, checked out in {options.mode} mode beside {directory.name}")
    record = Record(directory, options.mode)
    record.save(options.results)
    pins = entries(read_file(directory))
    record.pins, ok = resolve_and_report(directory, pins, options.mode)
    if ok:
        for entry in record.pins:
            if options.mode == "ci":
                entry.path = place_in_ci(directory, entry)
            else:
                entry.path = place_locally(directory, entry, options.worktrees)
            report(True, f"{entry.pin.repository} is at {entry.path}")
        record.checked_out = True
    record.save(options.results)
    if not pins:
        report(True, f"{directory} lists no counterpart: nothing to check")
        return Status.NOTHING_TO_CHECK
    note(f"recorded in {options.results / RECORD}")
    return Status.OK if ok else Status.FAIL


def ready_command(directory, options):
    print("Every pin, at merge time")
    document = read_file(directory)
    pins = [spec_pin(directory, document), *entries(document)]
    failed = 0
    with tempfile.TemporaryDirectory(dir=options.temporary, ignore_cleanup_errors=True) as scratch:
        ancestry = git.Ancestry(scratch)
        for pin in pins:
            branch = git.default_branch(pin.repository)
            if pin.kind == "branch":
                if pin.value == branch:
                    report(True, f"{pin}: the default branch")
                else:
                    failed += 1
                    report(
                        False,
                        f"{pin}: not the default branch, {branch}. A pull request may pin a "
                        "feature branch while both are open, and cannot merge that way",
                    )
                continue
            commit = pin.value if pin.kind == "commit" else git.remote_tag_commit(pin.repository, pin.value)
            if commit is None:
                failed += 1
                report(False, f"{pin}: names nothing in {pin.repository}")
            elif ancestry.on(pin.repository, branch, commit):
                report(True, f"{pin}: {commit} is on {branch}")
            else:
                failed += 1
                report(
                    False,
                    f"{pin}: {commit} is not on {branch}, the default branch. Pin its merge commit once it has merged",
                )
    return Status.FAIL if failed else Status.OK
