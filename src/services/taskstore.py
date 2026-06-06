import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Task:
    id: str
    title: str
    description: str = ""
    status: str = "todo"
    priority: str = "medium"
    labels: list[str] = field(default_factory=list)
    epic: str = ""
    subtasks: list[str] = field(default_factory=list)
    due_date: str = ""
    created_at: str = ""
    created_by: str = ""


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
TASKS_FILE = DATA_DIR / "tasks.json"


class TaskStore:

    def __init__(self):
        self._lock = None
        self._tasks: dict[str, Task] = {}
        self._loaded = False
        self._last_mtime: float = 0.0

    async def _ensure_loaded(self):
        if TASKS_FILE.exists():
            current_mtime = TASKS_FILE.stat().st_mtime
        else:
            current_mtime = 0
        if self._loaded and current_mtime <= self._last_mtime:
            return
        self._tasks = await self._read()
        self._last_mtime = current_mtime
        self._loaded = True

    async def _read(self) -> dict[str, Task]:
        if not TASKS_FILE.exists():
            return {}
        try:
            data = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
            return {tid: Task(**t) for tid, t in data.items()}
        except (json.JSONDecodeError, KeyError, TypeError):
            return {}

    async def _write(self):
        data = {tid: asdict(t) for tid, t in self._tasks.items()}
        TASKS_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    async def create(
        self,
        title: str,
        description: str = "",
        status: str = "todo",
        priority: str = "medium",
        labels: list[str] | None = None,
        epic: str = "",
        subtasks: list[str] | None = None,
        due_date: str = "",
        created_by: str = "",
    ) -> Task:
        await self._ensure_loaded()
        task = Task(
            id=uuid.uuid4().hex[:12],
            title=title,
            description=description,
            status=status,
            priority=priority,
            labels=labels or [],
            epic=epic,
            subtasks=subtasks or [],
            due_date=due_date,
            created_at=datetime.now(timezone.utc).isoformat(),
            created_by=created_by,
        )
        self._tasks[task.id] = task
        await self._write()
        return task

    async def get(self, task_id: str) -> Task | None:
        await self._ensure_loaded()
        return self._tasks.get(task_id)

    async def update(self, task_id: str, **kwargs) -> Task | None:
        await self._ensure_loaded()
        task = self._tasks.get(task_id)
        if task is None:
            return None
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        await self._write()
        return task

    async def delete(self, task_id: str) -> bool:
        await self._ensure_loaded()
        if task_id not in self._tasks:
            return False
        del self._tasks[task_id]
        await self._write()
        return True

    async def list_all(self) -> list[Task]:
        await self._ensure_loaded()
        return list(self._tasks.values())

    async def list_by_status(self) -> dict[str, list[Task]]:
        await self._ensure_loaded()
        grouped: dict[str, list[Task]] = {}
        for task in self._tasks.values():
            grouped.setdefault(task.status, []).append(task)
        return grouped

    async def update_status(self, task_id: str, status: str) -> Task | None:
        return await self.update(task_id, status=status)
