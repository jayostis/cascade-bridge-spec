# Validating an adapter package

What a conforming adapter package must satisfy, as **an RO-Crate profile**:
`cascade-bridge-adapter`, which declares itself `prof:isProfileOf` RO-Crate 1.2.
So an adapter is validated as an RO-Crate and as an adapter in one pass, against
one report, by `rocrate-validator` —
[`scripts/validate-adapter.py`](../scripts/validate-adapter.py) runs that profile
and prints what it found, and is what the published action
([`.github/actions/validate-adapter`](../.github/actions/validate-adapter/action.yml))
runs.

The requirements below are this specification's. Everything RO-Crate 1.2 requires
is inherited and is not restated here.

**A requirement is met or it is not, and any unmet requirement fails the run.**
Two consequences worth stating, because they are what a lint gets wrong:

- **A check that could not run reports an unmet requirement**, not silence. A
  machine without `lxml` has not satisfied the schema requirement; it never asked
  the question, and reporting nothing would let the silence read as an answer.
- **A check that ran and found nothing of its kind reports nothing.** An adapter
  whose manifest holds only `bridge:InputOnlyTest` entries has no expected graph,
  and has broken no rule: that type exists for exactly that case. There is
  nothing for its author to do, so there is nothing to say.

The one exception to the first is a package this lint has nothing against and
cannot read — a source schema declared JSON, which v1-draft does not specify.
That is a gap in the lint, not a fault in the package, and it is not reported as
a failure.

**Nothing an adapter names is fetched.** Digests are recomputed over the
committed bytes, and no publisher's file or referenced dataset is downloaded.
The tools do use the network, starting with the RO-Crate context the crate names.

What each requirement reports, in its own words, is
[`scripts/unittest-lint.py`](../scripts/unittest-lint.py): one test per decision,
each named for the sentence it asserts.

## The requirements

RO-Crate 1.2 conformance comes first, inherited: an adapter package is an
RO-Crate before it is anything else, and the profile says so rather than this
list repeating it.

1. **The crate and the test manifest conform to the shapes.** The crate parsed
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
   something. `bridge:input`, `bridge:graph` and `bridge:findings` in the
   manifest, and `bridge:mapping`, `bridge:findingsQuery`, `bridge:detectQuery`,
   `bridge:sourceSchema` and `bridge:documentSchema` in the crate, are
   `sh:class schema:MediaObject`, what the RO-Crate 1.2 context expands `File`
   to, so a mistyped name fails: an IRI naming no entity is still an IRI. And
   every declared `encodingFormat` is one of the media types below.

   And they carry what can be asserted about queries the lint does not run: the
   adapter names at least one `bridge:mapping` and exactly one
   `bridge:detectQuery`, every query it names is declared
   `application/sparql-query`, and it requires `bridge:sparql-1.1`.

2. **Every git-tracked file is accounted for.** Each file in the repository is
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

3. **Every digest matches its file.** A crate records two kinds of claim about
   a file's bytes, and they are not the same assertion
   ([`fixtures/README.md`](fixtures/README.md)). Both are
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

   The publisher's file is **not fetched**: its digest is already recorded in
   the crate, which is the point of recording it. A digest on an entity whose
   bytes are not committed — a referenced release, a pinned commit — is
   recorded, counted and not compared, and the run says how many.

4. **Every input validates against the declared schema.** For each test in the
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
   than committed is not fetched; and a **source schema declared JSON** is
   outside v1-draft, which specifies XML sources, so the lint says it could not
   read it and holds the package to nothing. A schema declared XML that does not
   compile as an XSD is a different matter and fails.

5. **Every expected graph parses.** Each `bridge:graph` as Turtle. Parsing, not
   conforming: an expected graph is what a mapping must produce, and judging it
   against Cascade's shapes is the Bridge's validate stage, not the lint's job
   — a lint that judged a fixture against them would report it as wrong for
   recording something Cascade has no term for yet, which is exactly what the
   findings sidecar beside it is for. The lint says so in its own output, so
   that a pass here is never read as more than "this file is Turtle".

6. **Every query parses as SPARQL 1.1, in the form its property declares.**
   Each file `bridge:mapping`, `bridge:findingsQuery` and `bridge:detectQuery`
   names, parsed by rdflib: a mapping is a CONSTRUCT, a findings query a SELECT
   projecting `?sourceField ?reason ?severity ?context`, in any order and no
   other variable, and the detect query an ASK.

A package that meets every requirement above, and RO-Crate 1.2's own, is a
conforming adapter package. None of them runs a mapping or compares a graph:
that is the test manifest, and it needs a Bridge ([`fixtures/manifest.md`](fixtures/manifest.md)).

## The media types an adapter package may declare

The allowed set is the `sh:in` list on `<#DescribedFile>` in
[`shapes/bridge.shapes.ttl`](../shapes/bridge.shapes.ttl), and a run that trips
on it prints the whole set in the violation. That is the set; it is not copied
here, because a copy is how a package comes to declare a media type the shapes
reject.

The set is deliberately short, and it is where "no code" is enforced. A format an
adapter needs and this set lacks is a pull request here, argued once, rather than
a media type invented in one adapter's crate. `encodingFormat` is a string rather
than a PRONOM IRI: RO-Crate 1.2 allows either, and a set of two spellings is a
set that can disagree with itself.

## The specification pin

An adapter states the revision of this specification it is written against
once, as `bridge:specPin` in its crate. The lint reads it and reports the commit
and the repository it names, and compares it with nothing: the starter checks
this repository out at exactly that commit before the lint runs, so the revision
running is the pinned one by construction. A pin that names no `version` or no
`codeRepository` fails the run.

Whether the pinned commit is on this repository's default branch is a
merge-time question, and the merge gate asks it: `ready`, in
[`../compatibility.md`](../compatibility.md).

## The lint as a reusable action

The checks are published as a composite GitHub Action,
`.github/actions/validate-adapter`, for the reason in
[`../pinning.md`](../pinning.md). An adapter's CI does not call it directly. It
calls the starter, at a tag that never moves:

```yaml
jobs:
  adapter:
    runs-on: ubuntu-latest
    steps:
      - uses: jayostis/cascade-bridge-spec/.github/actions/start@start-v1
  ready-to-merge:
    runs-on: ubuntu-latest
    steps:
      - uses: jayostis/cascade-bridge-spec/.github/actions/start@start-v1
        with:
          check: ready-to-merge
```

That is the whole of it: two jobs, the second the merge gate, meant to be a
required status check. Bumping the pin is an edit to the crate and nothing else.
What the starter reads, checks out and hands over to is
[`../compatibility.md`](../compatibility.md).

The run ends by listing every requirement with the word it earned, so a package
is never reported as meeting one that was never checked.

## Running it

```bash
python3 -m pip install pyshacl rdflib roc-validator lxml
python3 scripts/validate-adapter.py <path to an adapter checkout>
```

Exit status is 0 when every requirement is met and 1 when any is not. CI on
this project's repositories is Linux and invokes `python3` directly;
do not commit a machine-specific way of running it.

