import os
import tempfile
import unittest

from app import create_app


class TeamTaskManagerTests(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE": self.db_path,
                "SECRET_KEY": "test-secret",
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def signup(self, name, email, role):
        return self.client.post(
            "/api/auth/signup",
            json={"name": name, "email": email, "password": "secret1", "role": role},
        )

    def test_admin_can_create_project_and_task(self):
        admin = self.signup("Ada Admin", "ada@example.com", "Admin").get_json()["user"]
        self.client.post("/api/auth/logout")
        member = self.signup("Mina Member", "mina@example.com", "Member").get_json()["user"]
        self.client.post("/api/auth/logout")
        self.client.post("/api/auth/login", json={"email": "ada@example.com", "password": "secret1"})

        project_response = self.client.post(
            "/api/projects",
            json={"name": "Launch", "description": "Event prep", "member_ids": [member["id"]]},
        )
        self.assertEqual(project_response.status_code, 201)
        project = project_response.get_json()["project"]

        task_response = self.client.post(
            "/api/tasks",
            json={
                "project_id": project["id"],
                "title": "Confirm vendors",
                "assignee_id": member["id"],
                "status": "Todo",
                "due_date": "2030-01-10",
            },
        )
        self.assertEqual(task_response.status_code, 201)
        self.assertEqual(task_response.get_json()["task"]["assignee_id"], member["id"])

        dashboard = self.client.get("/api/dashboard").get_json()
        self.assertEqual(dashboard["total"], 1)

    def test_member_cannot_create_project(self):
        self.signup("Mina Member", "mina@example.com", "Member")
        response = self.client.post("/api/projects", json={"name": "Blocked"})
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
