"""One module per check of adapter/validation.md, in the order it names them."""

from . import digests, graphs, inputs, inventory, queries, shapes, specpin

__all__ = [
    "shapes",
    "inventory",
    "digests",
    "inputs",
    "graphs",
    "queries",
    "specpin",
]
