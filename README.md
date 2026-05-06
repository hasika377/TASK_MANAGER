# Team Task Manager

A full-stack Flask + SQLite app for managing projects, teams, assigned tasks, status updates, and overdue work with Admin/Member role-based access control.
Team Task Manager is a full-stack web application for creating projects, assigning team tasks, and tracking progress with role-based access control.

## Live Demo

Add your Railway deployment URL here after deployment:

```text
https://your-railway-app-url.up.railway.app
```

## Tech Stack

- Backend: Python Flask
- Frontend: HTML, CSS, JavaScript
- Database: SQLite
- Authentication: Flask sessions with hashed passwords
- Deployment: Railway
- Production server: Gunicorn

## Features

- Signup and login with hashed passwords
- User signup and login
- Admin and Member roles
- Admin project creation and team membership management
- Task creation, assignment, due dates, and status tracking
- Member-scoped task updates
- Dashboard totals by status and overdue tasks
- REST API backed by relational SQLite tables
- Railway-ready `Procfile` and `requirements.txt`
- Admin-only project creation
- Project team/member management
- Task creation and assignment
- Task status tracking: Todo, In Progress, Done
- Dashboard with total, status-wise, and overdue task counts
- REST APIs with validations and database relationships
- Railway-ready deployment configuration

## Role-Based Access

### Admin

- Create projects
- Add members to projects
- Create and assign tasks
- View all projects and tasks
- Update task details and status

### Member

- View assigned/project tasks
- Create tasks assigned to themselves
- Update status of their assigned tasks
- View personal dashboard

## Project Structure

```text
team-task-manager/
|-- app.py
|-- requirements.txt
|-- Procfile
|-- runtime.txt
|-- README.md
|-- tests.py
|-- static/
|   |-- app.js
|   `-- styles.css
`-- templates/
    `-- index.html
```

## Local Setup

1. Clone the repository:

```bash
git clone https://github.com/hasika377/team-task-manager.git
cd team-task-manager
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the application:

```bash
python app.py
```

Open `http://127.0.0.1:5000`.
5. Open the app:

## Demo Accounts
```text
http://127.0.0.1:5000
```

Create accounts from the signup screen. Choose `Admin` for the project manager account and `Member` for teammates.
## Demo Flow

## API Overview
1. Create an Admin account.
2. Create a Member account.
3. Login as Admin.
4. Create a project.
5. Add the Member to the project.
6. Create a task and assign it to the Member.
7. Update task status from Todo to In Progress or Done.
8. Show the dashboard statistics and overdue task tracking.

## API Endpoints

### Authentication

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/api/auth/signup` | Create a new user account |
| POST | `/api/auth/login` | Login user |
| POST | `/api/auth/logout` | Logout user |
| GET | `/api/me` | Get current logged-in user |

### Users

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/users` | List all users |

### Projects

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/projects` | List accessible projects |
| POST | `/api/projects` | Create a project |
| GET | `/api/projects/<id>` | Get project details |
| PUT | `/api/projects/<id>/members` | Update project members |

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
### Tasks

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/tasks` | List tasks |
| POST | `/api/tasks` | Create a task |
| PATCH | `/api/tasks/<id>` | Update task status/details |

### Dashboard

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/api/dashboard` | Get task summary and overdue statistics |

## Database Tables

- `users`
- `projects`
- `project_members`
- `tasks`

## Run Tests

```bash
python tests.py
```

## Railway Deployment

1. Push this project to GitHub.
2. Create a new Railway project from the GitHub repo.
3. Add environment variable `SECRET_KEY` with a strong random value.
4. Railway detects the Python app and runs `web: gunicorn app:app` from `Procfile`.
5. Copy the generated Railway domain for submission.
1. Push the project to GitHub.
2. Open Railway and create a new project.
3. Select Deploy from GitHub repo.
4. Choose this repository.
5. Add this environment variable:

```text
SECRET_KEY=your-strong-secret-key
```

6. Railway will install dependencies from `requirements.txt`.
7. Railway will start the app using the `Procfile`:

```text
web: gunicorn app:app
```

8. Copy the generated Railway domain and add it to the Live Demo section.






