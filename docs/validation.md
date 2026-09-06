# Validating an adapter package

What a conforming adapter package must pass, written as the list a lint
implements. The list is ordered so that the cheapest check that can fail comes
first and each later check can assume the earlier ones held.

Two of these run today, in
[`scripts/validate-adapter.py`](../scripts/validate-adapter.py): the RO-Crate
validation and the SHACL conformance. The rest are specified and not yet built.

## The list

1. **The package is a valid RO-Crate 1.2.**
   `rocrate-validator validate <adapter> --profile-identifier ro-crate-1.2`.
   Where the validator cannot be run, a JSON-LD parse is the floor, and whoever
   reports the result says which of the two ran.

2. **The crate and the test manifest conform to the shapes.** The crate parsed
   as JSON-LD with `ro-crate-metadata.json`'s own location as base, the test
   manifest parsed as Turtle with its own, loaded as **one graph**, validated
   against [`shapes/bridge.shapes.ttl`](../shapes/bridge.shapes.ttl) with a SHACL
   engine that supports SHACL-SPARQL (pySHACL, Jena). Both bases matter: with the
   wrong one, every link between the two files becomes two unrelated nodes and
   the shapes report nothing rather than reporting a mistake.

   The shapes carry the cross-file constraints as `sh:sparql`: the manifest's
   `bridge:adapter` and the adapter's `bridge:testManifest` point at each other,
   and every `bridge:envelope` a test action names is one the adapter lists.

3. **Every git-tracked file is accounted for.** Each file in the repository is
   either a crate entity carrying a declared `encodingFormat` in an allowed set,
   or is in a short allowlist: `README.md`, `LICENSE`, `CHANGELOG.md`,
   `CLAUDE.md`, and dotfiles (`.gitattributes`, `.editorconfig`, `.vscode/`,
   `.github/`).

   This is the check that makes "an adapter is data" a measured property rather
   than a claim. A file nobody described is a file nobody reviewed, and the
   allowed set of `encodingFormat` values is where "no code" is actually
   enforced — not by scanning for a language, but by refusing to accept a file
   whose media type says it executes.

4. **Every digest matches its file.** Each `sha256` in the crate is recomputed
   over the committed bytes. Where the publisher also publishes a digest, it is
   checked against the publisher's copy, and a mismatch is reported as a
   difference between the local copy and its source rather than as a corrupt
   file.

5. **Every input validates against the declared schema.** Each committed input
   under the fixtures, against the `bridge:documentSchema` of the envelope its
   test names, or against `bridge:sourceSchema` where the envelope declares none.

6. **Every expected graph parses.** Each `bridge:graph` as Turtle. Parsing, not
   conforming: an expected graph is what a mapping must produce, and judging it
   against Cascade's shapes is the Bridge's validate stage, not the lint's job.

A package that passes all six is a conforming adapter package. Nothing in the
list runs a mapping or compares a graph: that is the test manifest, and it needs
a Bridge ([`test-manifest.md`](test-manifest.md)).

## What the lint computes, and in what words

Beyond pass or fail, the lint reports one derived fact, and the wording is part
of the contract because a tier is a claim someone has to be able to re-verify:

- **`universal candidate`** — when the file inventory of check 3 found no code,
  and every profile in `bridge:profileRequired` is in Core.
- **`limited: requires <profiles>`** — otherwise, naming the profiles.

**Candidate, never universal.** RFC section 11: an adapter's tier is *measured*,
by running its fixtures on every published Bridge, and recorded in the
catalogue. A lint sees one package on one machine and can see only that nothing
disqualifies it. The word the lint may say is the strongest one the evidence
supports, and no adapter declares a tier of its own
([`adapter-manifest.md`](adapter-manifest.md)).

What is in Core is not yet settled — RFC section 9 proposes a SPARQL-only Core
and marks it as question 1 for the spike, against a prior of XSLT 3 for XML and
RML for JSON — so until that question is answered on
[spec#43](https://github.com/the-cascade-protocol/spec/issues/43), "every profile
is in Core" is decidable only for an adapter that requires no profiles at all.
An adapter that requires any profile is `limited: requires <profiles>` today,
and may be reclassified without changing a byte of the adapter when Core is
fixed. The pilot adapter requires `xslt-3` and is therefore
`limited: requires xslt-3`.

## The lint is a reusable GitHub Action, and it is not built

The six checks above will be published from this repository as a **reusable
GitHub Action**, so that an adapter repository's CI is one `uses:` line pinned
at a tag rather than six scripts copied between adapters. It does not exist yet.
What exists is `scripts/validate-adapter.py`, which runs checks 1 and 2 and is
what this repository's own CI runs against each catalogued adapter at its pinned
commit.

Building it is tracked as an issue in this repository. Two things it must keep
from the script as it stands: the base IRIs, for the reason in check 2; and the
naming of a missing `bridge:specPin` in its own words, because that is the one
failure every adapter written before this repository existed will hit, and a
generic "missing property" message would send its author looking in the wrong
file.

## Running the checks that exist

```bash
python3 -m pip install pyshacl rdflib roc-validator
python3 scripts/validate-adapter.py ../cascade-bridge-adapter-clinvar
```

Exit status is 0 when both checks pass and 1 when either fails. CI on this
project's repositories is Linux and invokes `python3` directly; do not commit a
machine-specific way of running it.
