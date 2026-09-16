from _crate import from_context


def held(check, context, find):
    """Add an issue for each message `find` yields for the package, and say
    whether the requirement held.

    A requirement that raised is unmet: it never asked its question, and the
    validator counts a check that raised as passed.
    """
    try:
        messages = list(find(from_context(context)))
    except Exception as error:
        messages = [f"could not be checked: {error}"]
    for message in messages:
        context.result.add_issue(message, check)
    return not messages
