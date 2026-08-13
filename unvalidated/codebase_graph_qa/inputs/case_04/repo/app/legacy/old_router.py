from app.db import connection


def setup_legacy():
    # not imported or called from anywhere in the app.main -> start() chain
    connection.get_pool()
