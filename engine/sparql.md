# The `sparql-1.1` profile

What a Bridge offering `bridge:sparql-1.1` does: lift XML to RDF, and run an
adapter's SPARQL 1.1 queries over the lift. A Bridge must reproduce the vectors
in [`../fixtures/lift/`](../fixtures/lift/).

## The lift

The lift turns one element, the lift root, and everything under it into
triples in the shape of SPARQL Anything's Facade-X. Every node is a blank node.

- **An element** is a node typed with an IRI naming it: its namespace IRI
  followed by its local name, or `http://sparql.xyz/facade-x/data/` followed by
  its local name when it has no namespace. The lift root is also typed
  `http://sparql.xyz/facade-x/ns/root`.
- **An attribute** is a triple from its element's node, whose predicate names
  the attribute the way an element's type names the element, and whose object
  is the attribute's value as a plain string literal. A namespace declaration
  is not an attribute.
- **An element's children**, elements and text in document order, are the
  objects of `rdf:_1`, `rdf:_2`, … from its node. A text child is a plain
  string literal holding its characters verbatim.
- **Dropped:** a text child made only of whitespace, comments, processing
  instructions, the document type declaration and the XML declaration. What is
  dropped takes no number. Whitespace is XML's `S` production, and no other
  character.

A name is appended to the namespace IRI as its own characters, each one outside
[RFC 3987's `iunreserved`](https://www.rfc-editor.org/rfc/rfc3987#section-2.2)
percent-encoded as its UTF-8 octets.

## What is lifted

**A mapping and a findings query** run over one source record at a time, lifted
with the record's element as the lift root: nothing outside the record is lifted.
A record is an element whose local name is the adapter's
`bridge:elementNameOfEachRecord`, in any namespace or none; a record inside
another is not specified.

**The detect query** runs over the document's *envelope skeleton*: the lift of
the whole document, with the document element as the lift root, except that
every record is lifted as an empty container — its type triples and its place
among its parent's children, without its attributes or its children. A record
that is the document element is lifted as an empty container too: the skeleton
is then its type triples alone.

## Running an adapter

A Bridge runs every source record of a document whatever the adapter's
`bridge:detectQuery` answers, and reports the answer.

For each source record of a document, in document order, a Bridge:

1. lifts the record into the default graph of an empty dataset;
2. loads every `bridge:table` declared `text/turtle` into the same default
   graph. No other table format is specified;
3. runs every `bridge:mapping`, a CONSTRUCT, over that dataset. The record's
   graph is the union of their results;
4. runs every `bridge:findingsQuery`, a CONSTRUCT, over the same dataset. The
   record's findings are the union of their graphs, with `bridge:thisRecord`
   replaced by the IRI the Bridge was given for the document the record was
   read from — the entry's `bridge:input` as [`executing.md`](executing.md)
   resolves it under `test`, the `<document>` argument as an absolute `file:`
   IRI under `convert` — and each annotation's selector moved under that
   record's own selector as its `oa:refinedBy`. Each annotation gets a selector
   of its own, and an annotation whose query constructed none is about the
   record itself: its target carries the record's selector and no
   `oa:refinedBy`.
5. adds, where the adapter names a `bridge:sourceAccounting`, one finding for
   each distinct path of the record that no `bridge:PathEntry` of that file
   carries as its `bridge:sourcePath`. An adapter naming none gets none.

A path is the element and attribute names from the record element down to the
node, the record element first, separated by `/`, an attribute's last step
written `@name`, no step carrying a position. The record element itself is no
path, so every census finding is refined under the record's selector. A path is
the same under every envelope the adapter declares, because it starts at the
record rather than at the document.

A census finding is addressed at the path's first occurrence in the record,
refined under the record's selector as any other finding is, and carries
`bridge:pathNotAccounted` as its body, the path as its `sh:value`, and
`sh:Info` as its `sh:resultSeverity`. A finding about an attribute is refined
onto the element the attribute stands on, and names the attribute in `sh:value`.

A `bridge:sourceAccounting` a crate names and a Bridge cannot read is an error,
as one that does not parse is. Naming none is the silent case.

Each annotation a findings query constructs targets a blank node written for
that one annotation, `[ oa:hasSource bridge:thisRecord ]`; a query says the
record itself by constructing no selector on it. A name, one labelled blank node
two annotations share, and a variable bound to a node the lift already holds are
each one node for more than one finding, so which selector standing on it
belongs to which finding is unrecoverable.

A record's selector is the XPath from the document element to the record: a
step for the document element, then one for each element down to and including
the record, however deep it is. Every step below the document element carries
`[n]`, its position among its own siblings of that name, counting from 1.

A step names an element in no namespace by that name. A step names an element
in a namespace by `*[local-name()='…' and namespace-uri()='…']`, because an
XPath carries no prefix bindings and a selector is read where nothing can
supply them.

A finding a Bridge makes about the document rather than about a record selects
the document element, and is refined under it as a record's finding is refined
under the record.

A finding about a source document breaking its schema carries as its body the
anchor of the rule broken, in the XML Schema Recommendation that defines it,
read from the validator's code up to its first dot: `cvc-complex-type.2.4` is
`https://www.w3.org/TR/xmlschema-1/#cvc-complex-type`. A code neither Part
names carries `bridge:schemaRuleUnnamed`. Which Part defines a rule is not a
choice: the adapter profile refuses a body naming the other, and lists every
anchor a body may take. Each rule a node breaks is a finding of its own,
refined to that node.
