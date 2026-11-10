"""What the tests page shows of a case, written into the case's report as properties: a heading for each class around the
test, from its docstring, and the test's own title and description. The page reads them as the runtime's does."""

import functools
import inspect
import re

import pytest

RULE = re.compile(r"^@rule[ \t]+(.+)$", re.MULTILINE)
HUMP = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def said(thing, name):
    """What a test class or a test says of itself on the page: its title, the first paragraph of its docstring, or with
    no docstring its name in words; its description, the paragraphs after; and each `@rule <feature> <id>` line."""
    text = inspect.getdoc(thing) or ""
    paragraphs = [" ".join(part.split()) for part in RULE.sub("", text).split("\n\n") if part.strip()]
    title = paragraphs[0] if paragraphs else in_words(name)
    return title, "\n\n".join(paragraphs[1:]), [rule.strip() for rule in RULE.findall(text)]


def in_words(name):
    """`test_is_a_select` as "is a select", `TestGivenAnyQuery` as "given any query"."""
    if name.startswith("test_"):
        return name.removeprefix("test_").replace("_", " ")
    return HUMP.sub(" ", name.removeprefix("Test")).lower()


@functools.cache
def line(thing):
    return inspect.getsourcelines(thing)[1]


def page_properties(item):
    """The properties the tests page reads from a case's report: each class around the test as `describe:N:*`, outermost
    first, and the test's own title and description. A parametrized case's title ends with its id in brackets. A
    parametrized case whose docstring gives no description says what it shows in its `says` mark."""
    found = []
    classes = [node for node in item.listchain() if isinstance(node, pytest.Class)]
    for at, node in enumerate(classes, start=1):
        title, description, rules = said(node.obj, node.name)
        found += [(f"describe:{at}:title", title), (f"describe:{at}:line", str(line(node.obj)))]
        found += [(f"describe:{at}:description", description)] if description else []
        found += [(f"describe:{at}:rule", rule) for rule in rules]
    title, description, rules = said(item.function, item.originalname)
    callspec = getattr(item, "callspec", None)
    found.append(("title", f"{title} [{callspec.id}]" if callspec else title))
    mark = item.get_closest_marker("says")
    description = description or (" ".join(str(mark.args[0]).split()) if mark and mark.args else "")
    found += [("description", description)] if description else []
    found += [("rule", rule) for rule in rules]
    return found
