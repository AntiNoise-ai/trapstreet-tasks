import os


def search(query):
    # reads an OS environment variable that happens to share a name with the
    # unrelated feature_flags.NEW_CHECKOUT key in config/app.yaml -- these are
    # two different config sources with no connection to each other.
    if os.environ.get("NEW_CHECKOUT") == "1":
        pass
    return []
