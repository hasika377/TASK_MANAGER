const state = {
  user: null,
  users: [],
  projects: [],
  tasks: [],
  signup: false,
};

const $ = (selector) => document.querySelector(selector);
const api = async (path, options = {}) => {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    ...options,
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
};

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  boot();
});

function bindEvents() {
  $("#toggleAuth").addEventListener("click", () => {
    state.signup = !state.signup;
    $("#authTitle").textContent = state.signup ? "Create account" : "Log in";
    $("#toggleAuth").textContent = state.signup ? "Use existing account" : "Create account";
    $("#nameField").classList.toggle("hidden", !state.signup);
    $("#roleField").classList.toggle("hidden", !state.signup);
  });

  $("#authForm").addEventListener("submit", submitAuth);
  $("#logoutBtn").addEventListener("click", logout);
  $("#newProjectBtn").addEventListener("click", () => $("#projectDialog").showModal());
  $("#newTaskBtn").addEventListener("click", () => $("#taskDialog").showModal());
  $("#projectForm").addEventListener("submit", submitProject);
  $("#taskForm").addEventListener("submit", submitTask);
  $("#projectFilter").addEventListener("change", loadTasks);
  $("#statusFilter").addEventListener("change", renderTasks);
  document.querySelectorAll("[data-close]").forEach((button) => {
    button.addEventListener("click", () => button.closest("dialog").close());
  });
}

async function boot() {
  try {
    const data = await api("/api/me");
    state.user = data.user;
    await loadApp();
  } catch {
    showAuth();
  }
}

async function submitAuth(event) {
  event.preventDefault();
  const form = new FormData(event.target);
  const body = Object.fromEntries(form.entries());
  try {
    const data = await api(state.signup ? "/api/auth/signup" : "/api/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    });
    state.user = data.user;
    $("#authError").textContent = "";
    await loadApp();
  } catch (error) {
    $("#authError").textContent = error.message;
  }
}

async function logout() {
  await api("/api/auth/logout", { method: "POST" });
  state.user = null;
  showAuth();
}

async function loadApp() {
  $("#authView").classList.add("hidden");
  $("#appView").classList.remove("hidden");
  $("#currentUser").textContent = `${state.user.name} · ${state.user.role}`;
  document.querySelectorAll(".admin-only").forEach((el) => {
    el.classList.toggle("hidden", state.user.role !== "Admin");
  });
  const [users, projects, dashboard] = await Promise.all([
    api("/api/users"),
    api("/api/projects"),
    api("/api/dashboard"),
  ]);
  state.users = users.users;
  state.projects = projects.projects;
  renderUsers();
  renderProjects();
  renderDashboard(dashboard);
  await loadTasks();
}

function showAuth() {
  $("#appView").classList.add("hidden");
  $("#authView").classList.remove("hidden");
}

function renderDashboard(data) {
  $("#totalTasks").textContent = data.total || 0;
  $("#todoTasks").textContent = data.by_status.Todo || 0;
  $("#progressTasks").textContent = data.by_status["In Progress"] || 0;
  $("#overdueTasks").textContent = data.overdue || 0;
}

function renderUsers() {
  const options = state.users
    .map((user) => `<option value="${user.id}">${escapeHtml(user.name)} (${user.role})</option>`)
    .join("");
  $("#projectMembers").innerHTML = options;
  $("#taskAssignee").innerHTML = options;
}

function renderProjects() {
  $("#projectsList").innerHTML = state.projects.length
    ? state.projects.map(projectCard).join("")
    : `<p class="meta">No projects yet.</p>`;
  $("#projectFilter").innerHTML =
    `<option value="">All projects</option>` +
    state.projects.map((p) => `<option value="${p.id}">${escapeHtml(p.name)}</option>`).join("");
  $("#taskProject").innerHTML = state.projects
    .map((p) => `<option value="${p.id}">${escapeHtml(p.name)}</option>`)
    .join("");
}

function projectCard(project) {
  return `
    <article class="item">
      <h3>${escapeHtml(project.name)}</h3>
      <p class="meta">${escapeHtml(project.description || "No description")}</p>
      <span class="badge">${project.member_count || 1} members</span>
      <span class="badge">${project.task_count || 0} tasks</span>
    </article>
  `;
}

async function loadTasks() {
  const projectId = $("#projectFilter").value;
  const data = await api(`/api/tasks${projectId ? `?project_id=${projectId}` : ""}`);
  state.tasks = data.tasks;
  renderTasks();
}

function renderTasks() {
  const status = $("#statusFilter").value;
  const tasks = status ? state.tasks.filter((task) => task.status === status) : state.tasks;
  $("#tasksList").innerHTML = tasks.length
    ? tasks.map(taskCard).join("")
    : `<p class="meta">No tasks match this view.</p>`;
  document.querySelectorAll("[data-status]").forEach((button) => {
    button.addEventListener("click", () => updateStatus(button.dataset.id, button.dataset.status));
  });
}

function taskCard(task) {
  const nextActions = ["Todo", "In Progress", "Done"]
    .filter((status) => status !== task.status)
    .map((status) => `<button class="secondary" data-id="${task.id}" data-status="${status}">${status}</button>`)
    .join("");
  return `
    <article class="task">
      <div class="task-top">
        <div>
          <h3>${escapeHtml(task.title)}</h3>
          <p class="meta">${escapeHtml(task.project_name)} · ${escapeHtml(task.assignee_name)} · due ${task.due_date}</p>
        </div>
        <span class="badge ${task.is_overdue ? "overdue" : ""}">${task.status}</span>
      </div>
      <p class="meta">${escapeHtml(task.description || "No description")}</p>
      <div class="task-actions">${nextActions}</div>
    </article>
  `;
}

async function submitProject(event) {
  event.preventDefault();
  const form = new FormData(event.target);
  const body = {
    name: form.get("name"),
    description: form.get("description"),
    member_ids: form.getAll("member_ids"),
  };
  try {
    await api("/api/projects", { method: "POST", body: JSON.stringify(body) });
    event.target.reset();
    $("#projectDialog").close();
    showToast("Project created");
    await loadApp();
  } catch (error) {
    showToast(error.message);
  }
}

async function submitTask(event) {
  event.preventDefault();
  const body = Object.fromEntries(new FormData(event.target).entries());
  try {
    await api("/api/tasks", { method: "POST", body: JSON.stringify(body) });
    event.target.reset();
    $("#taskDialog").close();
    showToast("Task created");
    await loadApp();
  } catch (error) {
    showToast(error.message);
  }
}

async function updateStatus(id, status) {
  try {
    await api(`/api/tasks/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
    showToast("Task updated");
    await loadApp();
  } catch (error) {
    showToast(error.message);
  }
}

function showToast(message) {
  $("#toast").textContent = message;
  $("#toast").classList.remove("hidden");
  setTimeout(() => $("#toast").classList.add("hidden"), 2800);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[char]));
}
