from _crate import from_context


def held(check, context, find):
    try:
        messages = list(find(from_context(context)))
    except Exception as error:
        # rocrate-validator counts a check that raised as passed:
        # https://github.com/crs4/rocrate-validator/issues/199
        messages = [f"could not be checked: {error}"]
    for message in messages:
        context.result.add_issue(message, check)
    return not messages
