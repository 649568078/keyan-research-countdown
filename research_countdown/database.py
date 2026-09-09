import sqlite3

from flask import current_app, g


SCHEMA = """
CREATE TABLE IF NOT EXISTS countdowns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    start_date TEXT NOT NULL,
    deadline TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '其他',
    description TEXT NOT NULL DEFAULT '',
    color TEXT NOT NULL DEFAULT '#536dfe',
    completed INTEGER NOT NULL DEFAULT 0,
    archived INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (deadline >= start_date)
);

CREATE TABLE IF NOT EXISTS milestones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    countdown_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    start_date TEXT NOT NULL,
    deadline TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    completed INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (countdown_id) REFERENCES countdowns (id) ON DELETE CASCADE,
    CHECK (deadline >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_milestones_countdown
ON milestones (countdown_id, sort_order, deadline);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_database(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA)
        columns = {row["name"] for row in db.execute("PRAGMA table_info(countdowns)")}
        if "archived" not in columns:
            db.execute(
                "ALTER TABLE countdowns ADD COLUMN archived INTEGER NOT NULL DEFAULT 0"
            )
        db.commit()
