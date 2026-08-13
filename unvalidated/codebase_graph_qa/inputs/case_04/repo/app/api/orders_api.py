from app.db import connection


def register():
    connection.get_pool()
