from _crate import from_context


def report_findings(check, context, find):
    try:
        messages = list(find(from_context(context)))
    except Exception as error:
        messages = [f"could not be checked: {error}"]
    for message in messages:
        context.result.add_issue(message, check)
    return not messages
