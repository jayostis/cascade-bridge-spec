# Validating an adapter package

What a conforming adapter package must pass, written as the list a lint
implements. The list is ordered so that the cheapest check that can fail comes
first and each later check can assume the earlier ones held.

All six run, in [`scripts/validate-adapter.py`](../scripts/validate-adapter.py),
which is what the published action
([`.github/actions/validate-adapter`](../.github/actions/validate-adapter/action.yml))
runs.

**Every check says whether it ran**, and the words are part of the contract,
because the failure this list is written against is a check that quietly did
nothing and was read as a pass:

| word | what it means | fails the run |
|---|---|---|
| `ok` | the check ran and everything it asked for held | no |
| `FAIL` | the check ran and something did not hold | yes |
| `nothing to check` | the check ran and found nothing of its kind in this package | no |
| `not run` | the check did not happen | yes, unless the reason is that the package is outside what the lint reads rather than that a tool is missing |

`ok` and `nothing to check` are different sentences and are printed as
different sentences. An adapter with no expected graph has not *passed* check
6; it has given check 6 nothing to disbelieve. A machine where `lxml` is not
installed has not passed check 5 either: it never asked the question, and the
run fails so that nobody reads the silence as an answer. The one case where a
check that did not happen leaves the run green is a package the lint has
nothing against and cannot read — a source schema that is a JSON Schema, check
5 below — and even there the word printed is `not run`.

**Nothing in the list reaches the network.** Digests are recomputed over the
committed bytes and no publisher's file is fetched, so the lint runs offline
and in a CI job with no credentials.

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

   They also carry the two constraints that make an IRI naming a file mean
   something. Every file-valued property — `bridge:input`, `bridge:graph`,
   `bridge:findings`, `bridge:sourceSchema`, `bridge:documentSchema` — is
   `sh:class schema:MediaObject`, what the RO-Crate 1.2 context expands `File`
   to, so a mistyped name fails instead of conforming; `sh:nodeKind sh:IRI`
   alone let a typo through, because an IRI naming no entity at all is still an
   IRI. And every declared `encodingFormat` is one of the media types below.

3. **Every git-tracked file is accounted for.** Each file in the repository is
   either a crate entity carrying a declared `encodingFormat`, or is in a short
   allowlist: `README.md`, `LICENSE`, `CHANGELOG.md`, `CLAUDE.md`,
   `ro-crate-metadata.json`, and dotfiles (`.gitattributes`, `.editorconfig`,
   `.vscode/`, `.github/`).

   `ro-crate-metadata.json` is in the allowlist for a different reason from the
   other four. It is not undescribed: it is the crate's own metadata descriptor,
   the entity every RO-Crate must carry and the one entity RO-Crate 1.2 forbids
   from being a data entity in `hasPart`. It therefore has no `encodingFormat`
   and cannot be given one.

   The inventory is taken with `git ls-files`, not a directory walk: a walk sees
   build output, a virtual environment and whatever the last run left behind, and
   an inventory that counts those is an inventory nobody can keep green.

   This is the check that makes "an adapter is data" a measured property rather
   than a claim. A file nobody described is a file nobody reviewed, and the
   allowed set of `encodingFormat` values is where "no code" is actually
   enforced — not by scanning for a language, but by refusing to accept a file
   whose media type says it executes.

4. **Every digest matches its file.** A crate records two kinds of claim about
   a file's bytes, and they are not the same assertion
   ([`fixtures-and-provenance.md`](fixtures-and-provenance.md)). Both are
   recomputed over the committed bytes; **a mismatch in each is a different
   finding and is reported in different words.**

   - `sha256` — what the RO-Crate 1.2 context expands `sha256` to — is the
     **local claim**: these bytes, here, now. A mismatch says *the crate's
     record is wrong about the file beside it*: one of the two was changed and
     the other was not.
   - Every other digest property on the same entity — an `md5` copied out of
     the `.md5` a publisher publishes beside its file, in whatever namespace
     the crate writes it — is the **publisher's claim** about the file at its
     source. Recomputing it over the committed bytes asks a different question,
     and a mismatch says *this copy has drifted from the source it claims to be
     a byte-for-byte copy of*. The realistic shape of it: the publisher
     republished, someone copied the new digest and did not re-fetch the bytes.
     Sending that author to check the crate would send them to the wrong file.

   The publisher's file is **not fetched**, here or anywhere in this list. A
   lint that needed the network is a lint that cannot run offline or in a CI
   job without credentials, and the publisher's digest is already recorded in
   the crate, which is the point of recording it. A digest on an entity whose
   bytes are not committed — a referenced release, a pinned commit — is
   recorded, counted and not compared, and the run says how many.

5. **Every input validates against the declared schema.** For each test in the
   test manifest, the committed `bridge:input` of its action against the
   `bridge:documentSchema` of the envelope that test names, or against the
   adapter's `bridge:sourceSchema` where that envelope declares none. An
   envelope declares a document schema exactly when its document root is not
   the one the source schema declares, so the fallback is the ordinary case
   and not an error path.

   XSD 1.0 is the engine, by `lxml`. Three outcomes are not failures of the
   package and are reported as themselves rather than as passes: a test whose
   action names a `bridge:dataset` has no committed bytes here, and the Bridge
   that streams them validates them; a schema entity that is referenced rather
   than committed cannot be read offline; and a **source schema that is a JSON
   Schema** is a real adapter this lint does not read yet, reported `not run`.
   A schema declared XML that does not compile as an XSD is a different matter
   and fails.

6. **Every expected graph parses.** Each `bridge:graph` as Turtle. Parsing, not
   conforming: an expected graph is what a mapping must produce, and judging it
   against Cascade's shapes is the Bridge's validate stage, not the lint's job
   — a lint that judged a fixture against them would report it as wrong for
   recording something Cascade has no term for yet, which is exactly what the
   findings sidecar beside it is for. The lint says so in its own output, so
   that a pass here is never read as more than "this file is Turtle".

A package that passes all six is a conforming adapter package. Nothing in the
list runs a mapping or compares a graph: that is the test manifest, and it needs
a Bridge ([`test-manifest.md`](test-manifest.md)).

## The media types an adapter package may declare

The allowed set for check 3, enforced by the shapes as `<#DescribedFile>` so
that it runs rather than only being written down.
[`shapes/bridge.shapes.ttl`](../shapes/bridge.shapes.ttl) is the authority; this
table restates it, and the two change in the same commit.

| media type | what declares it |
|---|---|
| `application/gzip` | a referenced release published as an archive |
| `application/json` | a findings sidecar, a lookup table's source |
| `application/ld+json` | a crate, a context |
| `application/sparql-query` | a mapping under a SPARQL profile |
| `application/xml` | a source document, an XSD |
| `application/xslt+xml` | a mapping under the `xslt-3` profile |
| `application/yaml` | a manifest or table an adapter carries as YAML |
| `text/csv` | a lookup table that arrives as one |
| `text/markdown` | a document under `docs/` |
| `text/plain` | a NOTICE, a checksum sidecar |
| `text/turtle` | a test manifest, an expected graph, a SKOS table, an RML mapping |
| `text/xml` | the other spelling of XML, which publishers do use |

The set is deliberately short, and it is where "no code" is enforced. A format an
adapter needs and this set lacks is a pull request here, argued once, rather than
a media type invented in one adapter's crate. `encodingFormat` is a string rather
than a PRONOM IRI: RO-Crate 1.2 allows either, every adapter written so far uses
the media type, and a set of two spellings is a set that can disagree with
itself.

## What the lint computes, and in what words

Beyond pass or fail, the lint reports one derived fact, and the wording is part
of the contract because a tier is a claim someone has to be able to re-verify:

- **`universal candidate`** — when the file inventory of check 3 found no code,
  and every profile in `bridge:profileRequired` is in Core.
- **`limited: requires <profiles>`** — otherwise, naming the profiles.

**Candidate, never universal.** RFC section 11: an adapter's tier is *measured*,
by running its fixtures on every published Bridge, and recorded in a catalogue —
a repository downstream of every adapter and every Bridge, which does not exist
yet ([`alignment.md`](alignment.md)). A lint sees one package on one machine and
can see only that nothing disqualifies it. The word the lint may say is the
strongest one the evidence supports, and no adapter declares a tier of its own
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

## The specification pin is checked against the ref the lint was called at

An adapter states the revision of this specification it is written against
twice: as `bridge:specPin` in its crate, for the reader, and as the ref its
workflow calls the action at, for the machine. They are the same fact, so the
lint holds them to it. The action resolves its own ref to a SHA and hands it to
the script as `--spec-revision`; a crate pinning a different commit fails the
run. Where the ref cannot be resolved — the action was called by a local path, or
the network refused — the pin is reported and not compared, and the run says
which of the two happened. A check that silently checks nothing is worse than no
check.

## The lint as a reusable action

The checks are published from this repository as a **composite GitHub Action**,
so that an adapter repository's CI is one `uses:` line pinned at a tag rather
than the checks copied between adapters. Copied checks are the failure this
repository exists to prevent: a second statement of a fact is one that can
disagree.

```yaml
      - uses: actions/checkout@v4
      - uses: jayostis/cascade-bridge-spec/.github/actions/validate-adapter@v0.3.0
        with:
          path: .          # the default; the directory holding ro-crate-metadata.json
```

All six checks run. The action ends by printing each of them with the word it
earned, so a package is never reported as passing a check that did not happen.

Three things the action keeps from the script, and must go on keeping:

- **The base IRIs**, set explicitly, for the reason in check 2.
- **The naming of a missing `bridge:specPin` in its own words.** That is the one
  failure every adapter written before this repository existed will hit, and a
  generic "missing property" message would send its author looking in the wrong
  file. The wording is `the crate is valid and the manifest conforms except for
  the missing bridge:specPin`.
- **Knowing no adapter.** It takes a directory. It names no repository, no
  format id and no package, and it clones nothing but the caller's own checkout.

## Running the checks

```bash
python3 -m pip install pyshacl rdflib roc-validator lxml
python3 scripts/validate-adapter.py <path to an adapter checkout>
```

Exit status is 0 when every check passes and 1 when any fails or could not be
run. CI on this project's repositories is Linux and invokes `python3` directly;
do not commit a machine-specific way of running it.

