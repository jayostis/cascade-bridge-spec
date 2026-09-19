def local_name_of(node):
    tag = getattr(node, "tag", None)
    return tag.rpartition("}")[2] if isinstance(tag, str) else None


def namespace_of(node):
    tag = getattr(node, "tag", "")
    return tag[1:].partition("}")[0] if isinstance(tag, str) and tag.startswith("{") else ""


def step_of(element, indexed):
    name = local_name_of(element)
    namespace = namespace_of(element)
    written = name if not namespace else f"*[local-name()='{name}' and namespace-uri()='{namespace}']"
    if not indexed:
        return written
    parent = element.getparent()
    alike = [other for other in parent if other.tag == element.tag]
    return f"{written}[{alike.index(element) + 1}]"


def selector_of(element):
    steps, walked = [], element
    while walked is not None:
        steps.append(step_of(walked, walked.getparent() is not None))
        walked = walked.getparent()
    return "/" + "/".join(reversed(steps))
