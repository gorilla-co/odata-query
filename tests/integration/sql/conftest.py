import sqlite3

import pytest


@pytest.fixture(scope="session")
def db_conn():
    conn = sqlite3.connect(":memory:", isolation_level=None)
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def db_schema(db_conn):
    cur = db_conn.cursor()

    cur.execute("CREATE TABLE author (id INTEGER PRIMARY KEY, name TEXT);")
    cur.execute(
        "CREATE TABLE blogpost ("
        "id INTEGER PRIMARY KEY, "
        "published_at TEXT, "
        "title TEXT, "
        "content TEXT);"
    )
    cur.execute(
        "CREATE TABLE comment ("
        "id INTEGER PRIMARY KEY, "
        "content TEXT, "
        "author_id INTEGER, "
        "blogpost_id INTEGER, "
        "FOREIGN KEY (author_id) REFERENCES author(id), "
        "FOREIGN KEY (blogpost_id) REFERENCES blogpost(id)"
        ");"
    )
    cur.execute(
        "CREATE TABLE author_blogpost ("
        "author_id INTEGER, "
        "blogpost_id INTEGER, "
        "FOREIGN KEY (author_id) REFERENCES author(id), "
        "FOREIGN KEY (blogpost_id) REFERENCES blogpost(id)"
        ");"
    )
    db_conn.commit()
