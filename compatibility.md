# Compatibility between engines and adapters

Every engine and every adapter pins one thing: this specification. Anything more
is opt-in. A repository may commit a `compatibility.json` saying "also test me
against this adapter" (in an engine) or "against this engine" (in an adapter).
**Every entry is an assertion, and a failed assertion blocks the merge.** To stop
an entry blocking, edit the file.

[`pinning.md`](pinning.md) is why pins work this way. This document is the file,
what each entry asserts, and the tooling that checks it.

## The file

`compatibility.json`, at the repository root. It is JSON that is also JSON-LD:
its `@context` is the string
`https://ns.cascadeprotocol.org/bridge/v1-draft/compatibility.jsonld`, which,
like the profile IRI, does not dereference yet;
[`vocab/compatibility.context.jsonld`](vocab/compatibility.context.jsonld) is the
context it names. It is validated by SHACL, like a crate and a test manifest,
against [`shapes/bridge.shapes.ttl`](shapes/bridge.shapes.ttl). The terms are in
[`vocab/bridge.ttl`](vocab/bridge.ttl).

An engine's file:

```json
{
  "@context": "https://ns.cascadeprotocol.org/bridge/v1-draft/compatibility.jsonld",
  "specification": {
    "codeRepository": "https://github.com/jayostis/cascade-bridge-spec",
    "commit": "7a614179c4856a3f6e1a4b5a6c90a183b0c7c99a"
  },
  "setup": ["npm", "ci"],
  "command": ["node", "packages/bridge-cli/src/cli.ts"],
  "testedWith": [
    {
      "codeRepository": "https://github.com/jayostis/cascade-bridge-adapter-clinvar",
      "branch": "main"
    }
  ]
}
```

An adapter's file, which has no `specification`, `setup` or `command`:

```json
{
  "@context": "https://ns.cascadeprotocol.org/bridge/v1-draft/compatibility.jsonld",
  "testedWith": [
    {
      "codeRepository": "https://github.com/jayostis/cascade-bridge-rs",
      "commit": "54a30dcc743d6367723b7a365065d45271835740"
    }
  ]
}
```

| key | term | in an engine's file | in an adapter's file | value |
|---|---|---|---|---|
| `specification` | `bridge:specification` | exactly 1 | none | a pin naming this repository |
| `setup` | `bridge:setup` | exactly 1 | none | an argument vector: an array of at least one string |
| `command` | `bridge:command` | exactly 1 | none | an argument vector: an array of at least one string |
| `testedWith` | `bridge:testedWith` | 0 or more | 0 or more | a pin; each repository at most once |

Which form applies is decided by the directory, not by the file: a directory
holding `ro-crate-metadata.json` is an adapter, and one without is an engine.
The shapes accept either form; the tooling holds the form to the directory.

- **An adapter's spec pin stays in its crate**, as `bridge:specPin`, because a
  host loading an adapter reads the crate. An engine has no crate, so it states
  its pin here.
- **`setup` and `command` are argument vectors, run without a shell**, in the
  engine's checkout, so one file works on Windows and on Linux CI. This
  repository learns no language's build; the engine states its own.
- **`command` receives `test <adapter directory> --earl <file>`**, the contract
  every engine meets ([`engine/command.md`](engine/command.md)).
- **Every key is one the context defines.** JSON-LD drops a key its context does
  not define, so a misspelt `testedwith` would otherwise be a file asserting
  nothing, read as a file asserting something. The tooling refuses it.
- **In an adapter, the crate lists `compatibility.json`** as a file like any
  other, declared `application/ld+json`, so the lint's inventory accounts for it.

## Pins

A pin names a repository by `codeRepository`, its absolute URL, and exactly one
of:

| key | term | resolves to |
|---|---|---|
| `commit` | `schema:version` | itself: a full 40-character SHA |
| `tag` | `bridge:tag` | the commit the tag names |
| `branch` | `bridge:branch` | the branch's tip in CI. Locally, the sibling's working tree when the sibling is on that branch; otherwise the branch's last commit, with a warning |

`commit` is `schema:version` because that is what the entity `bridge:specPin`
names already carries for the SHA: one pin, one shape.

**Every run records what each pin resolved to**: the commit, and a flag when the
sibling's uncommitted edits were used. A result produced from uncommitted edits
is feedback, never evidence.

**What each kind guarantees.** A commit or tag pin is reproducible: a pull
request green on it stays green once merged. A default-branch pin
(`"branch": "main"`) means "keep me current, and block me when the other side
breaks me": the other repository merging something can turn this one red with
no change of its own, and the file records that choice.

### At merge time

The `ready-to-merge` check, meant to be a required status check, holds every pin
— the specification pin, from the crate for an adapter and from this file for an
engine, and every entry — to one rule:

- a pin may be a commit or a tag on the counterpart's default branch, or the
  counterpart's default branch itself;
- a pin to any other branch is refused.

So a pull request can pin the other side's feature branch while both are in
flight, and cannot merge that way. A tag is accepted when the commit it names is
on the default branch; there is no separate commit-only rule. The default branch
is read from the counterpart (`git ls-remote --symref <url> HEAD`), never
assumed to be `main`.

## When an entry holds

An entry **holds** when the engine ran the adapter's test manifest and no test's
outcome in the EARL report is `earl:failed` or `earl:inapplicable`.
`earl:passed`, `earl:cantTell` and `earl:untested` hold.

- **The report decides, not the exit code.** An engine's exit code carries no
  meaning the tooling relies on.
- **No report is not a pass.** A run that wrote no report, a report that does not
  parse as Turtle, and a report recording no outcome at all do not hold. Nor
  does an outcome that is not one of EARL's five.
- **The adapter's own manifest decides what should pass.** The file records no
  expected counts.

## Changing an entry

- **Opt out** by deleting the entry, or by re-pinning it to a version that
  passes. There is no "expected to fail" entry; git history and the pull request
  carry the reason.
- **Add a pairing after both sides have merged**, so that a new assertion cannot
  deadlock two open pull requests.
- **A breaking change resolves in the open.** The engine's pull request removes
  or re-pins the affected adapter entry and merges. The adapter follows in its
  own pull request against the new engine. The engine re-adds the entry at the
  adapter's new commit.

## Sibling layout

Every repository sits beside the others under one directory, named exactly as
its repository: the last segment of its `codeRepository`, without `.git`. The
tooling looks for a counterpart at `../<repository name>`.

- **Locally**, a branch pin uses the sibling as it is, uncommitted edits
  included, when the sibling is on that branch. A commit or tag pin runs from a
  temporary `git worktree` of the sibling at that commit, under the system
  temporary directory, and the sibling's working copy is left untouched.
- **In CI**, each counterpart is cloned at its resolved commit beside the
  repository under test, inside the workspace: GitHub's checkout cannot write
  outside it, so the repository under test sits in its own named subdirectory
  too.
- **A missing sibling stops the run** with the `git clone` command that fixes
  it. Nothing is cloned into a developer's directory unasked.
- **A counterpart that cannot be reached** — private, renamed or deleted — stops
  the run with a message naming the repository, not a raw git error.

## The tooling

[`scripts/compatibility.py`](scripts/compatibility.py) is one tool, and needs
`git`, `rdflib` and `pyshacl`. It takes directories and reads files: it names no
adapter and no engine.

| subcommand | does |
|---|---|
| `validate <dir>` | the directory's `compatibility.json` conforms to the shapes, and its form is the directory's |
| `resolve <dir>` | every pin resolves to a commit, and the resolution is printed and recorded |
| `checkout <dir>` | puts each counterpart beside the repository, as the layout above says |
| `run <dir>` | in an engine, runs its own `setup` and `command` on each listed adapter; in an adapter, runs each listed engine's `setup` and `command` on itself. Collects every EARL report |
| `judge [<dir>]` | applies the rule above to each report, one line per entry naming the resolved commit and any uncommitted-edits flag |
| `ready <dir>` | the merge-time rule |

Every subcommand reports in the words [`adapter/validation.md`](adapter/validation.md)
fixes — `ok`, `FAIL`, `nothing to check`, `not run` — and a repository with no
`compatibility.json` has nothing to check rather than a pass.

Three actions under `.github/actions/` run it in CI, and a repository's CI calls
only the first:

- **`start`**, published at the reserved tag `start-v1`, which never moves; a
  changed starter gets `start-v2`. It reads the repository's spec pin, checks
  this repository out at exactly that commit as a sibling, and hands over to the
  lint and the two actions below, run from that checkout. So the spec pin is
  written in exactly one place, and bumping it never touches the workflow.
- **`compatibility`**: `validate`, `checkout`, `run` and `judge`. The gating
  check. The EARL reports are the run's artifacts; nothing stores them here.
- **`ready-to-merge`**: `ready`.
