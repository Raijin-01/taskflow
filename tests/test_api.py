import csv
import io
import os
import tempfile
import unittest

from backend.app import create_app


class TaskApiTestCase(unittest.TestCase):
    def setUp(self):
        self.db_file = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.db_file.close()
        self.app = create_app(self.db_file.name)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        os.unlink(self.db_file.name)

    def create_task(self, **overrides):
        payload = {"title": "Write API tests", "description": "Cover endpoints",
                   "status": "todo", "priority": "medium", "assignee": "Test user"}
        payload.update(overrides)
        response = self.client.post("/api/tasks", json=payload)
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    def test_get_tasks_and_filters(self):
        self.create_task(title="Fix urgent bug", status="in_progress", priority="high")
        self.create_task(title="Write documentation", status="done", priority="low")
        self.create_task(title="Plan next sprint", status="todo", priority="high")
        self.assertEqual(self.client.get("/api/tasks").status_code, 200)
        self.assertEqual(len(self.client.get("/api/tasks").get_json()), 3)
        self.assertEqual(len(self.client.get("/api/tasks?status=done").get_json()), 1)
        self.assertEqual(len(self.client.get("/api/tasks?priority=high").get_json()), 2)
        response = self.client.get("/api/tasks?q=urgent")
        self.assertEqual([task["title"] for task in response.get_json()], ["Fix urgent bug"])

    def test_create_task_validation(self):
        response = self.client.post("/api/tasks", json={"title": "A task"})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.client.post("/api/tasks", json={}).status_code, 400)
        self.assertEqual(self.client.post("/api/tasks", json={"title": "Bad", "status": "invalid"}).status_code, 400)

    def test_patch_task_and_missing_task(self):
        task = self.create_task()
        response = self.client.patch(f"/api/tasks/{task['id']}", json={"status": "done"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "done")
        self.assertEqual(self.client.patch("/api/tasks/99999", json={"status": "done"}).status_code, 404)

    def test_delete_task_and_missing_task(self):
        task = self.create_task()
        response = self.client.delete(f"/api/tasks/{task['id']}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"deleted": task["id"]})
        self.assertEqual(self.client.delete(f"/api/tasks/{task['id']}").status_code, 404)

    def test_stats_math(self):
        self.create_task(status="todo", priority="high")
        self.create_task(status="in_progress", priority="high")
        self.create_task(status="done", priority="high")
        self.create_task(status="done", priority="low")
        response = self.client.get("/api/stats")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"total": 4, "todo": 1, "in_progress": 1,
                                               "done": 2, "completion_pct": 50.0,
                                               "high_priority_open": 2})

    def test_csv_export_headers_and_content(self):
        task = self.create_task(title="Export me")
        response = self.client.get("/api/export.csv")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.content_type)
        rows = list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], str(task["id"]))
        self.assertEqual(rows[0]["title"], "Export me")
        self.assertEqual(set(rows[0]), {"id", "title", "description", "status", "priority", "assignee", "created_at"})


if __name__ == "__main__":
    unittest.main()
