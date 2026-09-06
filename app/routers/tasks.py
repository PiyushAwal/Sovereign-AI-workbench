from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import (
    AgentTask,
    Document,
    Project,
)
from app.schemas.schemas import (
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from app.services.audit_service import create_audit_log


router = APIRouter(
    prefix="/tasks",
    tags=["Agent Tasks"],
)


# ============================================================
# CREATE AI TASK
# ============================================================

@router.post("/", response_model=TaskResponse)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == task_data.project_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    if task_data.document_id:

        document = (
            db.query(Document)
            .filter(
                Document.id == task_data.document_id,
                Document.project_id == task_data.project_id,
            )
            .first()
        )

        if not document:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Document not found or does not "
                    "belong to the selected project"
                ),
            )

    task = AgentTask(
        project_id=task_data.project_id,
        document_id=task_data.document_id,
        task_type=task_data.task_type,
        description=task_data.description,
        status="pending",
        selected_model=task_data.selected_model,
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    create_audit_log(
        db=db,
        action="CREATE_AGENT_TASK",
        resource_type="agent_task",
        resource_id=task.id,
        details=(
            f"Task '{task.task_type}' created "
            f"for project {task.project_id}"
        ),
    )

    return task


# ============================================================
# GET ALL TASKS
# ============================================================

@router.get("/", response_model=list[TaskResponse])
def get_tasks(
    db: Session = Depends(get_db),
):
    return (
        db.query(AgentTask)
        .order_by(AgentTask.created_at.desc())
        .all()
    )


# ============================================================
# GET TASK
# ============================================================

@router.get(
    "/{task_id}",
    response_model=TaskResponse,
)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
):
    task = (
        db.query(AgentTask)
        .filter(AgentTask.id == task_id)
        .first()
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    return task


# ============================================================
# GET PROJECT TASKS
# ============================================================

@router.get(
    "/project/{project_id}",
    response_model=list[TaskResponse],
)
def get_project_tasks(
    project_id: int,
    db: Session = Depends(get_db),
):
    return (
        db.query(AgentTask)
        .filter(AgentTask.project_id == project_id)
        .order_by(AgentTask.created_at.desc())
        .all()
    )


# ============================================================
# UPDATE TASK
# ============================================================

@router.put(
    "/{task_id}",
    response_model=TaskResponse,
)
def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
):
    task = (
        db.query(AgentTask)
        .filter(AgentTask.id == task_id)
        .first()
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    update_data = task_data.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(task, key, value)

    if task.status in {
        "completed",
        "failed",
    }:
        task.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(task)

    create_audit_log(
        db=db,
        action="UPDATE_AGENT_TASK",
        resource_type="agent_task",
        resource_id=task.id,
        details=(
            f"Task status: {task.status}; "
            f"model: {task.selected_model}"
        ),
    )

    return task


# ============================================================
# START TASK
# ============================================================

@router.post("/{task_id}/start")
def start_task(
    task_id: int,
    db: Session = Depends(get_db),
):
    task = (
        db.query(AgentTask)
        .filter(AgentTask.id == task_id)
        .first()
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    task.status = "processing"

    if task.document_id:

        document = (
            db.query(Document)
            .filter(Document.id == task.document_id)
            .first()
        )

        if document:
            document.status = "processing"

    db.commit()

    create_audit_log(
        db=db,
        action="START_AGENT_TASK",
        resource_type="agent_task",
        resource_id=task.id,
        details="Agent task moved to processing",
    )

    return {
        "message": "Task started",
        "task_id": task.id,
        "status": task.status,
    }


# ============================================================
# COMPLETE TASK
# ============================================================

@router.post("/{task_id}/complete")
def complete_task(
    task_id: int,
    result: str,
    db: Session = Depends(get_db),
):
    task = (
        db.query(AgentTask)
        .filter(AgentTask.id == task_id)
        .first()
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    task.status = "completed"
    task.result = result
    task.completed_at = datetime.utcnow()

    if task.document_id:

        document = (
            db.query(Document)
            .filter(Document.id == task.document_id)
            .first()
        )

        if document:
            document.status = "completed"

    db.commit()
    db.refresh(task)

    create_audit_log(
        db=db,
        action="COMPLETE_AGENT_TASK",
        resource_type="agent_task",
        resource_id=task.id,
        details="Agent task completed successfully",
    )

    return {
        "message": "Task completed",
        "task_id": task.id,
        "status": task.status,
    }


# ============================================================
# FAIL TASK
# ============================================================

@router.post("/{task_id}/fail")
def fail_task(
    task_id: int,
    error_message: str,
    db: Session = Depends(get_db),
):
    task = (
        db.query(AgentTask)
        .filter(AgentTask.id == task_id)
        .first()
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    task.status = "failed"
    task.error_message = error_message
    task.completed_at = datetime.utcnow()

    if task.document_id:

        document = (
            db.query(Document)
            .filter(Document.id == task.document_id)
            .first()
        )

        if document:
            document.status = "failed"

    db.commit()
    db.refresh(task)

    create_audit_log(
        db=db,
        action="FAIL_AGENT_TASK",
        resource_type="agent_task",
        resource_id=task.id,
        details=error_message,
        success=False,
    )

    return {
        "message": "Task marked as failed",
        "task_id": task.id,
        "status": task.status,
    }