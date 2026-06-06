from dataclasses import asdict
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from web.state import store, broadcast, get_user_id

router = APIRouter()


@router.get("/api/tasks")
async def list_tasks():
    grouped = await store.list_by_status()
    serializable = {
        status: [asdict(t) for t in tasks]
        for status, tasks in grouped.items()
    }
    return JSONResponse(content=serializable)


@router.post("/api/tasks")
async def create_task(request: Request):
    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    body = await request.json()
    task = await store.create(
        title=body.get("title", "Untitled"),
        description=body.get("description", ""),
        status=body.get("status", "todo"),
        priority=body.get("priority", "medium"),
        labels=body.get("labels", []),
        epic=body.get("epic", ""),
        subtasks=body.get("subtasks", []),
        due_date=body.get("due_date", ""),
        created_by=user_id,
    )
    task_dict = asdict(task)
    await broadcast({"type": "task_created", "task": task_dict})
    return JSONResponse(content=task_dict, status_code=201)


@router.put("/api/tasks/{task_id}")
async def update_task(task_id: str, request: Request):
    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    body = await request.json()
    task = await store.update(task_id, **body)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task_dict = asdict(task)
    await broadcast({"type": "task_updated", "task": task_dict})
    return JSONResponse(content=task_dict)


@router.put("/api/tasks/{task_id}/status")
async def update_task_status(task_id: str, request: Request):
    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    body = await request.json()
    status = body.get("status")
    if status not in ("todo", "in_progress", "done"):
        raise HTTPException(status_code=400, detail="Invalid status")
    task = await store.update_status(task_id, status)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task_dict = asdict(task)
    await broadcast({"type": "task_updated", "task": task_dict})
    return JSONResponse(content=task_dict)


@router.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str, request: Request):
    user_id = get_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    deleted = await store.delete(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    await broadcast({"type": "task_deleted", "task_id": task_id})
    return JSONResponse(content={"ok": True})


@router.post("/api/refresh")
async def refresh_board():
    await store._ensure_loaded()
    await broadcast({"type": "task_refresh"})
    return JSONResponse(content={"ok": True})
