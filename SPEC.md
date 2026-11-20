# TaskFlow — Shared API & Project Contract

## Directory Ownership
- `backend/` — Flask app (`backend/app.py`), SQLite helper (`backend/db.py`), `backend/requirements.txt`
- `frontend/` — Static UI (`frontend/index.html`, `frontend/styles.css`, `frontend/app.js`)
- `tests/` — Automated tests (`tests/test_api.py`)

## Data Model (`tasks` table in SQLite)
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `title`: TEXT NOT NULL
- `description`: TEXT DEFAULT ""
- `status`: TEXT NOT NULL CHECK(status IN ('todo', 'in_progress', 'done')) DEFAULT 'todo'
- `priority`: TEXT NOT NULL CHECK(priority IN ('low', 'medium', 'high')) DEFAULT 'medium'
- `assignee`: TEXT DEFAULT "Unassigned"
- `created_at`: TEXT (ISO-8601 timestamp)

## REST API Contract (http://127.0.0.1:5000)
- `GET /` -> serves `frontend/index.html` and static assets (`styles.css`, `app.js`)
- `GET /api/tasks` -> list tasks (optional filters: `?status=`, `?priority=`, `?q=`)
- `POST /api/tasks` -> create task (`title` required; 201 + JSON, 400 if invalid)
- `PATCH /api/tasks/<int:task_id>` -> update any fields (200 + JSON, 404 if missing)
- `DELETE /api/tasks/<int:task_id>` -> delete task (200 + `{"deleted": id}`, 404 if missing)
- `GET /api/stats` -> `{"total": int, "todo": int, "in_progress": int, "done": int, "completion_pct": float, "high_priority_open": int}`
- `GET /api/export.csv` -> downloadable CSV of all tasks
