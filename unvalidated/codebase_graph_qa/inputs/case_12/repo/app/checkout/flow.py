from app.bootstrap import load_flags


def start_checkout():
    flags = load_flags()
    if flags["NEW_CHECKOUT"]:
        return _new_flow()
    return _old_flow()


def _new_flow():
    return "new"


def _old_flow():
    return "old"
