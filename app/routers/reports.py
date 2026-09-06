from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import (
    GeneratedReport,
    Project,
)
from app.schemas.schemas import (
    ReportCreate,
    ReportResponse,
)
from app.services.audit_service import create_audit_log


router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)


# ============================================================
# CREATE REPORT
# ============================================================

@router.post("/", response_model=ReportResponse)
def create_report(
    report_data: ReportCreate,
    db: Session = Depends(get_db),
):
    project = (
        db.query(Project)
        .filter(Project.id == report_data.project_id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    report = GeneratedReport(
        project_id=report_data.project_id,
        task_id=report_data.task_id,
        report_name=report_data.report_name,
        report_type=report_data.report_type,
        file_path=report_data.file_path,
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    create_audit_log(
        db=db,
        action="CREATE_REPORT",
        resource_type="report",
        resource_id=report.id,
        details=(
            f"Generated report '{report.report_name}'"
        ),
    )

    return report


# ============================================================
# GET ALL REPORTS
# ============================================================

@router.get(
    "/",
    response_model=list[ReportResponse],
)
def get_reports(
    db: Session = Depends(get_db),
):
    return (
        db.query(GeneratedReport)
        .order_by(GeneratedReport.created_at.desc())
        .all()
    )


# ============================================================
# GET REPORT
# ============================================================

@router.get(
    "/{report_id}",
    response_model=ReportResponse,
)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
):
    report = (
        db.query(GeneratedReport)
        .filter(GeneratedReport.id == report_id)
        .first()
    )

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found",
        )

    return report


# ============================================================
# PROJECT REPORTS
# ============================================================

@router.get(
    "/project/{project_id}",
    response_model=list[ReportResponse],
)
def get_project_reports(
    project_id: int,
    db: Session = Depends(get_db),
):
    return (
        db.query(GeneratedReport)
        .filter(
            GeneratedReport.project_id == project_id
        )
        .order_by(
            GeneratedReport.created_at.desc()
        )
        .all()
    )