# Team Task Manager

A full-stack Flask + SQLite app for managing projects, teams, assigned tasks, status updates, and overdue work with Admin/Member role-based access control.

## Features

- Signup and login with hashed passwords
- Admin and Member roles
- Admin project creation and team membership management
- Task creation, assignment, due dates, and status tracking
- Member-scoped task updates
- Dashboard totals by status and overdue tasks
- REST API backed by relational SQLite tables
- Railway-ready `Procfile` and `requirements.txt`

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

## Demo Accounts

Create accounts from the signup screen. Choose `Admin` for the project manager account and `Member` for teammates.

## API Overview

- `POST /api/auth/signup`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/me`
- `GET /api/users`
- `GET /api/projects`
- `POST /api/projects`
- `GET /api/projects/<id>`
- `PUT /api/projects/<id>/members`
- `GET /api/tasks`
- `POST /api/tasks`
- `PATCH /api/tasks/<id>`
- `GET /api/dashboard`

## Railway Deployment

1. Push this project to GitHub.
2. Create a new Railway project from the GitHub repo.
3. Add environment variable `SECRET_KEY` with a strong random value.
4. Railway detects the Python app and runs `web: gunicorn app:app` from `Procfile`.
5. Copy the generated Railway domain for submission.

## Submission Checklist

- Live Railway URL
- GitHub repository URL
- README
- 2-5 minute demo video showing signup/login, project creation, member assignment, task creation, status updates, and dashboard.
