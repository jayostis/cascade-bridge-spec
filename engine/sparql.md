# The `sparql-1.1` profile

What a Bridge offering `bridge:sparql-1.1` does: lift XML to RDF, and run an
adapter's SPARQL 1.1 queries over the lift. In v1-draft it is the one profile,
and every adapter requires it
([`../adapter/ro-crate-metadata.md`](../adapter/ro-crate-metadata.md)).

Two Bridges produce the same graph from one adapter only if they produce the
same lift, so the lift is specified exactly, and
[`../fixtures/lift/`](../fixtures/lift/) holds the vectors a Bridge's lift must
reproduce, each judged by `bridge:LiftTest`
([`../vocab/bridge.ttl`](../vocab/bridge.ttl)).

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
  string literal holding its characters verbatim. Character data and CDATA
  sections with nothing but dropped content between them are one text child.
- **Dropped:** a text child made only of whitespace, comments, processing
  instructions, the document type declaration and the XML declaration. What is
  dropped takes no number.

Every name in the vectors is ASCII. How a name with other characters is
written in an IRI is not specified in v1-draft.

## What is lifted

**A mapping and a findings query** run over one unit at a time, lifted with the
unit element as the lift root: nothing outside the unit is lifted. A unit is an
element whose local name is the adapter's `bridge:unit`; a unit's namespace,
and a unit inside another, are not specified.

**The detect query** runs over the document's *envelope skeleton*: the lift of
the whole document, with the document element as the lift root, except that
every unit is lifted as an empty container — its type triples and its place
among its parent's children, without its attributes or its children. A router
can build it while streaming, so detecting a multi-gigabyte release does not
mean lifting it.

## Running an adapter

`bridge:detectQuery`, an ASK over a document's envelope skeleton, is true when
the adapter handles the document. For each unit of a document it handles, in
document order, a Bridge:

1. lifts the unit into the default graph of an empty dataset;
2. loads every `bridge:table` declared `text/turtle` into the same default
   graph. No other table format is specified in v1-draft;
3. runs every `bridge:mapping`, a CONSTRUCT, over that dataset. The unit's
   graph is the union of their results;
4. runs every `bridge:findingsQuery`, a SELECT projecting exactly
   `?sourceField ?reason ?severity ?context`, over the same dataset. Each row is
   one finding: a JSON object with those four members, each the string the
   variable is bound to. The unit's findings are the rows of every findings
   query, concatenated; rows are not deduplicated.

The stages around this are [`stages.md`](stages.md).
