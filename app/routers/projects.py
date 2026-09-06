from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Project, User
from app.schemas.schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.audit_service import create_audit_log


router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)


# ============================================================
# CREATE PROJECT
# ============================================================

@router.post("/", response_model=ProjectResponse)
def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
):
    owner = (
        db.query(User)
        .filter(User.id == project_data.owner_id)
        .first()
    )

    if not owner:
        raise HTTPException(
            status_code=404,
            detail="Project owner not found",
        )

    project = Project(
        name=project_data.name,
        description=project_data.description,
        owner_id=project_data.owner_id,
        status="active",
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    create_audit_log(
        db=db,
        action="CREATE_PROJECT",
        resource_type="project",
        resource_id=project.id,
        user_id=project.owner_id,
        details=f"Project '{project.name}' created",
    )

    return project


# ============================================================
# GET ALL PROJECTS
# ============================================================

@router.get("/", response_model=list[ProjectResponse])
def get_projects(
    db: Session = Depends(get_db),
):
    return (
        db.query(Project)
        .order_by(Project.created_at.desc())
        .all()
    )


# ============================================================
# GET PROJECT
# ============================================================

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    return project


# ============================================================
# UPDATE PROJECT
# ============================================================

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    update_data = project_data.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)

    create_audit_log(
        db=db,
        action="UPDATE_PROJECT",
        resource_type="project",
        resource_id=project.id,
        user_id=project.owner_id,
        details=f"Project '{project.name}' updated",
    )

    return project


# ============================================================
# DELETE PROJECT
# ============================================================

@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    project_name = project.name
    owner_id = project.owner_id

    db.delete(project)
    db.commit()

    create_audit_log(
        db=db,
        action="DELETE_PROJECT",
        resource_type="project",
        resource_id=project_id,
        user_id=owner_id,
        details=f"Project '{project_name}' deleted",
    )

    return {
        "message": "Project deleted successfully",
        "project_id": project_id,
    }


# ============================================================
# PROJECT DASHBOARD SUMMARY
# ============================================================

@router.get("/{project_id}/summary")
def project_summary(
    project_id: int,
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == project_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    return {
        "project_id": project.id,
        "project_name": project.name,
        "status": project.status,
        "owner_id": project.owner_id,
        "document_count": len(project.documents),
        "task_count": len(project.agent_tasks),
    }