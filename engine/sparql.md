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
  string literal holding its characters verbatim. Character data and CDATA
  sections with nothing but dropped content between them are one text child.
- **Dropped:** a text child made only of whitespace, comments, processing
  instructions, the document type declaration and the XML declaration. What is
  dropped takes no number. Whitespace is XML's `S` production: space, tab,
  carriage return and line feed, and no other character. A no-break space is
  text, alone or beside spaces.

How a non-ASCII name is written in an IRI is not specified.

## What is lifted

**A mapping and a findings query** run over one source record at a time, lifted
with the record's element as the lift root: nothing outside the record is lifted.
A record is an element whose local name is the adapter's
`bridge:elementNameOfEachRecord`; a record's namespace, and a record inside
another, are not specified.

**The detect query** runs over the document's *envelope skeleton*: the lift of
the whole document, with the document element as the lift root, except that
every record is lifted as an empty container — its type triples and its place
among its parent's children, without its attributes or its children. A record
that is the document element is lifted as an empty container too: the skeleton
is then its type triples alone.

## Running an adapter

For each source record of a document the adapter's `bridge:detectQuery`
accepts, in document order, a Bridge:

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

A findings query's `oa:hasTarget` is a blank node. A name is one node for every
finding the query produces, so which selector standing on it belongs to which
finding is unrecoverable; a query says the record itself by targeting
`[ oa:hasSource bridge:thisRecord ]` and constructing no selector.

A record's selector is its position: `/` the envelope's document root element,
`/` the record element, `[n]`, n counting records of that name from 1 in
document order. Where the document root element is the record element, the
selector is that one step and not two.
