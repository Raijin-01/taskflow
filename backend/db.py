"""SQLite setup and access helpers for TaskFlow."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone


SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    status TEXT NOT NULL CHECK(status IN ('todo', 'in_progress', 'done')) DEFAULT 'todo',
    priority TEXT NOT NULL CHECK(priority IN ('low', 'medium', 'high')) DEFAULT 'medium',
    assignee TEXT DEFAULT 'Unassigned',
    created_at TEXT
)
"""

SEED_TASKS = (
    ("Plan product launch", "Finalize the launch checklist and owners.", "in_progress", "high", "Maya"),
    ("Design onboarding flow", "Create wireframes for the first-run experience.", "todo", "medium", "Jordan"),
    ("Set up analytics", "Add event tracking for the main dashboard actions.", "todo", "low", "Unassigned"),
    ("Review security controls", "Run through the quarterly access review.", "done", "high", "Priya"),
    ("Publish release notes", "Prepare customer-facing notes for the latest release.", "done", "medium", "Leo"),
)


@contextmanager
def connect(db_path):
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize_database(db_path):
    with connect(db_path) as connection:
        connection.execute(SCHEMA)
        if connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0:
            now = datetime.now(timezone.utc).isoformat()
            connection.executemany(
                """INSERT INTO tasks
                   (title, description, status, priority, assignee, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                [task + (now,) for task in SEED_TASKS],
            )

