let currentUser = null;
let currentTaskId = null;
let editing = false;

const STATUSES = ["todo", "in_progress", "done"];

async function api(path, options = {}) {
  const resp = await fetch(path, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!resp.ok && resp.status === 401) {
    currentUser = null;
    updateAuthUI();
    return null;
  }
  return resp.json();
}

async function checkAuth() {
  const data = await api("/auth/me");
  if (data && data.authenticated) {
    currentUser = data;
  } else {
    currentUser = null;
  }
  updateAuthUI();
}

function updateAuthUI() {
  const loginArea = document.getElementById("login-area");
  const userInfo = document.getElementById("user-info");
  const userName = document.getElementById("user-name");
  const addBtn = document.getElementById("add-task-btn");

  if (currentUser) {
    loginArea.classList.add("hidden");
    userInfo.classList.remove("hidden");
    userName.textContent = currentUser.user_name || "User";
    addBtn.classList.remove("hidden");
  } else {
    loginArea.classList.remove("hidden");
    userInfo.classList.add("hidden");
    addBtn.classList.add("hidden");
  }
}

async function loadBoard() {
  const columns = document.getElementById("col-todo");
  const data = await api("/api/tasks");
  if (!data) return;

  for (const status of STATUSES) {
    const col = document.getElementById("col-" + status);
    col.innerHTML = "";
    const tasks = data[status] || [];
    for (const task of tasks) {
      col.appendChild(createCard(task));
    }
  }
}

function createCard(task) {
  const card = document.createElement("div");
  card.className = "card";
  card.dataset.id = task.id;

  const title = document.createElement("div");
  title.className = "card-title";
  title.textContent = task.title;

  const meta = document.createElement("div");
  meta.className = "card-meta";

  const prio = document.createElement("span");
  prio.className = "badge badge-" + task.priority;
  prio.textContent = task.priority;
  meta.appendChild(prio);

  if (task.epic) {
    const ep = document.createElement("span");
    ep.className = "badge badge-epic";
    ep.textContent = task.epic;
    meta.appendChild(ep);
  }

  for (const label of (task.labels || [])) {
    const lb = document.createElement("span");
    lb.className = "badge badge-label";
    lb.textContent = label;
    meta.appendChild(lb);
  }

  if (task.due_date) {
    const dd = document.createElement("span");
    dd.textContent = "due " + task.due_date;
    meta.appendChild(dd);
  }

  const idEl = document.createElement("span");
  idEl.className = "card-id";
  idEl.textContent = "#" + task.id.slice(0, 6);

  card.appendChild(title);
  card.appendChild(meta);
  card.appendChild(idEl);

  card.addEventListener("click", () => openModal(task.id));
  return card;
}

function renderBoard(grouped) {
  for (const status of STATUSES) {
    const col = document.getElementById("col-" + status);
    col.innerHTML = "";
    const tasks = grouped[status] || [];
    for (const task of tasks) {
      col.appendChild(createCard(task));
    }
  }
}

function initSortable() {
  for (const status of STATUSES) {
    const el = document.getElementById("col-" + status);
    new Sortable(el, {
      group: "kanban",
      animation: 150,
      ghostClass: "sortable-ghost",
      chosenClass: "sortable-chosen",
      onEnd: async (evt) => {
        const taskId = evt.item.dataset.id;
        const newCol = evt.to.id.replace("col-", "");
        if (!currentUser) {
          toast("Login to move tasks");
          loadBoard();
          return;
        }
        await api("/api/tasks/" + taskId + "/status", {
          method: "PUT",
          body: JSON.stringify({ status: newCol }),
        });
      },
    });
  }
}

function openModal(taskId) {
  currentTaskId = taskId;
  editing = true;
  document.getElementById("modal-title").textContent = "Edit Task";
  document.getElementById("delete-task-btn").classList.remove("hidden");
  document.getElementById("task-modal").classList.remove("hidden");

  const card = document.querySelector(`.card[data-id="${taskId}"]`);
  if (!card) return;
  const title = card.querySelector(".card-title").textContent;
  document.getElementById("edit-title").value = title;
  document.getElementById("edit-description").value = "";
  document.getElementById("edit-priority").value = "medium";
  document.getElementById("edit-status").value = card.closest("[data-status]")?.dataset?.status || "todo";
  document.getElementById("edit-labels").value = "";
  document.getElementById("edit-epic").value = "";
  document.getElementById("edit-due_date").value = "";
}

function openNewTaskModal() {
  currentTaskId = null;
  editing = false;
  document.getElementById("modal-title").textContent = "New Task";
  document.getElementById("delete-task-btn").classList.add("hidden");
  document.getElementById("edit-title").value = "";
  document.getElementById("edit-description").value = "";
  document.getElementById("edit-priority").value = "medium";
  document.getElementById("edit-status").value = "todo";
  document.getElementById("edit-labels").value = "";
  document.getElementById("edit-epic").value = "";
  document.getElementById("edit-due_date").value = "";
  document.getElementById("task-modal").classList.remove("hidden");
}

function closeModal() {
  document.getElementById("task-modal").classList.add("hidden");
  currentTaskId = null;
}

async function saveTask() {
  const data = {
    title: document.getElementById("edit-title").value,
    description: document.getElementById("edit-description").value,
    priority: document.getElementById("edit-priority").value,
    status: document.getElementById("edit-status").value,
    labels: document.getElementById("edit-labels").value.split(",").map(s => s.trim()).filter(Boolean),
    epic: document.getElementById("edit-epic").value,
    due_date: document.getElementById("edit-due_date").value,
  };

  if (!data.title) { toast("Title is required"); return; }

  if (editing && currentTaskId) {
    await api("/api/tasks/" + currentTaskId, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  } else {
    await api("/api/tasks", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }
  closeModal();
}

async function deleteTask() {
  if (!currentTaskId) return;
  if (!confirm("Delete this task?")) return;
  await api("/api/tasks/" + currentTaskId, { method: "DELETE" });
  closeModal();
}

function connectWebSocket() {
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(proto + "//" + location.host + "/ws");

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    switch (msg.type) {
      case "task_created":
      case "task_updated":
      case "task_deleted":
      case "task_refresh":
        loadBoard();
        break;
    }
  };

  ws.onclose = () => {
    setTimeout(connectWebSocket, 2000);
  };

  ws.onerror = () => ws.close();
}

let pollInterval = null;

function startPolling() {
  if (pollInterval) clearInterval(pollInterval);
  pollInterval = setInterval(loadBoard, 15000);
}

function toast(message) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 3000);
}

async function init() {
  await checkAuth();
  await loadBoard();
  initSortable();
  connectWebSocket();
  startPolling();

  document.getElementById("add-task-btn").addEventListener("click", openNewTaskModal);
  document.getElementById("save-task-btn").addEventListener("click", saveTask);
  document.getElementById("delete-task-btn").addEventListener("click", deleteTask);

  const modal = document.getElementById("task-modal");
  modal.querySelector(".modal-close").addEventListener("click", closeModal);
  modal.querySelector(".modal-backdrop").addEventListener("click", closeModal);

  document.getElementById("logout-btn").addEventListener("click", () => {
    window.location.href = "/auth/logout";
  });
}

document.addEventListener("DOMContentLoaded", init);
