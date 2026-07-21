"""Task / timeline endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.store import store
from app.models.schemas import Task, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[Task])
def list_tasks() -> list[Task]:
    return store.list_tasks()


@router.patch("/{task_id}", response_model=Task)
def update_task(task_id: str, payload: TaskUpdate) -> Task:
    task = store.update_task_status(task_id, payload.status)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
