"""TaskFlow HTTP API."""

import csv
import io
import os
import sqlite3

from flask import Flask, Response, jsonify, request, send_from_directory

from .db import connect, initialize_database


VALID_STATUSES = {"todo", "in_progress", "done"}
VALID_PRIORITIES = {"low", "medium", "high"}
FIELDS = {"title", "description", "status", "priority", "assignee"}


def create_app(db_path=None):
    app = Flask(__name__)
    if db_path is None:
        db_path = os.path.join(os.path.dirname(__file__), "taskflow.sqlite3")
    initialize_database(db_path)
    app.config["DATABASE"] = db_path

    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

    def task_json(row):
        return dict(row)

    def error(message, status=400):
        return jsonify({"error": message}), status

    def payload():
        value = request.get_json(silent=True)
        if not isinstance(value, dict):
            return None, error("Request body must be a JSON object")
        unknown = set(value) - FIELDS
        if unknown:
            return None, error("Unknown field(s): " + ", ".join(sorted(unknown)))
        return value, None

    def validate(values, partial=False):
        if not partial and ("title" not in values or not isinstance(values.get("title"), str) or not values["title"].strip()):
            return "title is required"
        if "title" in values and (not isinstance(values["title"], str) or not values["title"].strip()):
            return "title must be a non-empty string"
        for field in ("description", "assignee"):
            if field in values and not isinstance(values[field], str):
                return f"{field} must be a string"
        if "status" in values and values["status"] not in VALID_STATUSES:
            return "status must be one of: todo, in_progress, done"
        if "priority" in values and values["priority"] not in VALID_PRIORITIES:
            return "priority must be one of: low, medium, high"
        return None

    @app.get("/")
    def index():
        return send_from_directory(frontend_dir, "index.html")

    @app.get("/<path:filename>")
    def frontend_assets(filename):
        if filename in {"styles.css", "app.js"}:
            return send_from_directory(frontend_dir, filename)
        return error("Not found", 404)

    @app.get("/api/tasks")
    def list_tasks():
        clauses, params = [], []
        if request.args.get("status") is not None:
            if request.args["status"] not in VALID_STATUSES:
                return error("invalid status filter")
            clauses.append("status = ?"); params.append(request.args["status"])
        if request.args.get("priority") is not None:
            if request.args["priority"] not in VALID_PRIORITIES:
                return error("invalid priority filter")
            clauses.append("priority = ?"); params.append(request.args["priority"])
        if request.args.get("q"):
            clauses.append("(title LIKE ? OR description LIKE ? OR assignee LIKE ?)")
            query = "%" + request.args["q"] + "%"; params.extend([query, query, query])
        sql = "SELECT * FROM tasks" + ((" WHERE " + " AND ".join(clauses)) if clauses else "") + " ORDER BY id"
        with connect(app.config["DATABASE"]) as db:
            rows = db.execute(sql, params).fetchall()
        return jsonify([task_json(row) for row in rows])

    @app.post("/api/tasks")
    def create_task():
        values, problem = payload()
        if problem: return problem
        message = validate(values)
        if message: return error(message)
        values.setdefault("description", ""); values.setdefault("status", "todo")
        values.setdefault("priority", "medium"); values.setdefault("assignee", "Unassigned")
        with connect(app.config["DATABASE"]) as db:
            cursor = db.execute("""INSERT INTO tasks (title, description, status, priority, assignee, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))""", tuple(values[field] for field in ("title", "description", "status", "priority", "assignee")))
            row = db.execute("SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return jsonify(task_json(row)), 201

    @app.patch("/api/tasks/<int:task_id>")
    def update_task(task_id):
        values, problem = payload()
        if problem: return problem
        message = validate(values, partial=True)
        if message: return error(message)
        if not values: return error("At least one field is required")
        with connect(app.config["DATABASE"]) as db:
            if db.execute("SELECT 1 FROM tasks WHERE id = ?", (task_id,)).fetchone() is None:
                return error("Task not found", 404)
            assignments = ", ".join(f"{field} = ?" for field in values)
            db.execute(f"UPDATE tasks SET {assignments} WHERE id = ?", tuple(values.values()) + (task_id,))
            row = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return jsonify(task_json(row))

    @app.delete("/api/tasks/<int:task_id>")
    def delete_task(task_id):
        with connect(app.config["DATABASE"]) as db:
            cursor = db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            if cursor.rowcount == 0: return error("Task not found", 404)
        return jsonify({"deleted": task_id})

    @app.get("/api/stats")
    def stats():
        with connect(app.config["DATABASE"]) as db:
            total = db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            counts = {row[0]: row[1] for row in db.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")}
            high_open = db.execute("SELECT COUNT(*) FROM tasks WHERE priority = 'high' AND status != 'done'").fetchone()[0]
        return jsonify({"total": total, "todo": counts.get("todo", 0), "in_progress": counts.get("in_progress", 0), "done": counts.get("done", 0), "completion_pct": round((counts.get("done", 0) / total * 100) if total else 0.0, 2), "high_priority_open": high_open})

    @app.get("/api/export.csv")
    def export_csv():
        with connect(app.config["DATABASE"]) as db:
            rows = db.execute("SELECT id, title, description, status, priority, assignee, created_at FROM tasks ORDER BY id").fetchall()
        output = io.StringIO(); writer = csv.writer(output)
        headers = ["id", "title", "description", "status", "priority", "assignee", "created_at"]
        writer.writerow(headers)
        writer.writerows([tuple(row) for row in rows])
        return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=tasks.csv"})

    return app


if __name__ == "__main__":
    create_app().run(debug=True)

