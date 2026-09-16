# vocab — Agent Context

`bridge.ttl` is the `bridge:` vocabulary, namespace
`https://ns.cascadeprotocol.org/bridge/v1-draft#`. Two groups in one namespace:
adapter terms, which are what an adapter says about itself in its RO-Crate, and
test terms, a small set on top of W3C's `mf:` test-manifest vocabulary the way
the SHACL test suite adds `sht:`.

- **Every term carries an `rdfs:comment`.** That is the vocabulary's payload, not
  decoration: it is what a reader dereferencing the namespace gets. A rule that
  belongs to a term goes there, where every adapter inherits it, rather than into
  a `#` header here or into a comment in some adapter's manifest.
- **A comparison rule belongs to its test class.** `bridge:IsomorphicConversionTest`
  and its siblings carry how they are judged. If an adapter's fixture manifest
  explains a comparison in a comment, the explanation is in the wrong repository.
- **No Cascade terms are minted here.** `bridge:` only. A term in `cascade:`,
  `genomics:` or any other Cascade vocabulary goes through spec's own process.
- **An adapter declares no tier**, so no term names one.
- **A term's cardinality goes in its `rdfs:comment`**, in words, because this is
  the only copy: `../adapter/ro-crate-metadata.md`,
  `../adapter/fixtures/manifest.md` and `../compatibility.md` name terms and give
  reasons, and list none of them. A reader sent here has to find it here.
- `compatibility.context.jsonld` is the JSON-LD context a `compatibility.json`
  names, and every key it defines is a term here or a schema.org term. Its IRI,
  like the profile IRI, does not dereference yet; `../scripts/compatibility.py`
  reads this file in its place.

It parses with `python3 -c "from rdflib import Graph; Graph().parse('vocab/bridge.ttl')"`.
