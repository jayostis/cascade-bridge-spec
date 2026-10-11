from compatibility_tool.github import DEPENDS_ON


def references(text):
    return DEPENDS_ON.findall(text or "")


def base_changed(event):
    return "base" in (event.get("changes") or {})


def depends_on_changed(event):
    changes = event.get("changes") or {}
    if "body" not in changes:
        return False
    before = references((changes["body"] or {}).get("from"))
    return before != references(event["pull_request"].get("body"))


def decide(event):
    if event.get("action") != "edited" or "pull_request" not in event:
        return []
    reasons = []
    if base_changed(event):
        reasons.append("the base changed")
    if depends_on_changed(event):
        reasons.append("the Depends-On: lines changed")
    return reasons
