import re

BOM = chr(0xFEFF)
SPACE = (
    " \t"
    + chr(0x0B)
    + chr(0x0C)
    + chr(0xA0)
    + chr(0x1680)
    + "".join(map(chr, range(0x2000, 0x200B)))
    + "".join(map(chr, (0x202F, 0x205F, 0x3000)))
)
LINE_END = re.compile("\r\n|[\n\r" + chr(0x2028) + chr(0x2029) + "]")
HEADING = re.compile(r"^##[ \t]+Breaking[ \t]*$")
ANY_HEADING = re.compile(r"^#{1,6}[ \t]")
RULE = re.compile(r"^-{3,}$")
DEPENDS_ON = re.compile(r"^Depends-On:", re.IGNORECASE | re.ASCII)
ITEM = re.compile(r"^(?:[-*+]|\d+\.)[ \t]+", re.ASCII)
NONE = re.compile(r"^none\.?$", re.IGNORECASE | re.ASCII)
ARROW = "->"


def is_old_to_new(line):
    old, arrow, new = line.partition(ARROW)
    return bool(arrow) and old.strip(SPACE) != "" and new.strip(SPACE) != ""


def problem_in(body):
    """What is wrong with the `## Breaking` section of a pull request's description, or None.

    The section ends at the next heading, a `---` rule or a `Depends-On:` line. The runtime repository's
    packages/cascade-runtime/pack/breaking.ts reads it the same way.
    """
    text = re.sub(r"<!--.*?-->", "", (body or "").replace(BOM, ""), flags=re.DOTALL)
    rows = LINE_END.split(text)
    start = next((index for index, row in enumerate(rows) if HEADING.match(row)), None)
    if start is None:
        return "the body has no `## Breaking` section"
    section = []
    for row in rows[start + 1 :]:
        trimmed = row.strip(SPACE)
        if ANY_HEADING.match(row) or RULE.match(trimmed) or DEPENDS_ON.match(trimmed):
            break
        section.append(row)
    lines = [ITEM.sub("", row.strip(SPACE)).strip(SPACE) for row in section]
    lines = [line for line in lines if line not in ("", "-", "*", "+")]
    if not lines:
        return "the `## Breaking` section is empty: list each `old -> new` or `old -> removed`, or write None"
    nones = sum(1 for line in lines if NONE.match(line))
    if nones == len(lines):
        return None
    if nones:
        return "the `## Breaking` section has None beside lines"
    loose = next((line for line in lines if not is_old_to_new(line)), None)
    if loose is not None:
        return f'"{loose}" is not `old -> new` or `old -> removed`'
    return None
