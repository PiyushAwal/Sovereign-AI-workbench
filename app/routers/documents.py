import os
import uuid

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Document, Project
from app.schemas.schemas import DocumentResponse
from app.services.audit_service import create_audit_log


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)


# ============================================================
# UPLOAD DOCUMENT
# ============================================================

@router.post(
    "/upload/{project_id}",
    response_model=DocumentResponse,
)
async def upload_document(
    project_id: int,
    file: UploadFile = File(...),
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

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid filename",
        )

    # --------------------------------------------------------
    # Supported industrial document formats
    # --------------------------------------------------------

    allowed_extensions = {
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".tiff",
        ".txt",
        ".csv",
        ".xlsx",
        ".docx",
    }

    extension = os.path.splitext(
        file.filename
    )[1].lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type: {extension}. "
                f"Allowed: {sorted(allowed_extensions)}"
            ),
        )

    # --------------------------------------------------------
    # Generate unique local filename
    # --------------------------------------------------------

    unique_filename = (
        f"{uuid.uuid4().hex}{extension}"
    )

    project_dir = os.path.join(
        UPLOAD_DIR,
        str(project_id),
    )

    os.makedirs(
        project_dir,
        exist_ok=True,
    )

    file_path = os.path.join(
        project_dir,
        unique_filename,
    )

    # --------------------------------------------------------
    # Save file locally
    # --------------------------------------------------------

    content = await file.read()

    with open(file_path, "wb") as buffer:
        buffer.write(content)

    file_size = len(content)

    # --------------------------------------------------------
    # Save metadata in PostgreSQL
    # --------------------------------------------------------

    document = Document(
        project_id=project_id,
        filename=file.filename,
        file_path=file_path,
        file_type=extension,
        file_size=file_size,
        status="pending",
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    create_audit_log(
        db=db,
        action="UPLOAD_DOCUMENT",
        resource_type="document",
        resource_id=document.id,
        details=(
            f"Document '{file.filename}' uploaded "
            f"to project {project_id}"
        ),
    )

    return document


# ============================================================
# GET ALL DOCUMENTS
# ============================================================

@router.get("/", response_model=list[DocumentResponse])
def get_documents(
    db: Session = Depends(get_db),
):
    return (
        db.query(Document)
        .order_by(Document.uploaded_at.desc())
        .all()
    )


# ============================================================
# GET PROJECT DOCUMENTS
# ============================================================

@router.get(
    "/project/{project_id}",
    response_model=list[DocumentResponse],
)
def get_project_documents(
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

    return (
        db.query(Document)
        .filter(Document.project_id == project_id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )


# ============================================================
# GET DOCUMENT
# ============================================================

@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    return document


# ============================================================
# UPDATE DOCUMENT STATUS
# ============================================================

@router.patch("/{document_id}/status")
def update_document_status(
    document_id: int,
    status: str,
    db: Session = Depends(get_db),
):
    allowed_statuses = {
        "pending",
        "processing",
        "completed",
        "failed",
    }

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid status. "
                f"Allowed: {sorted(allowed_statuses)}"
            ),
        )

    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    document.status = status

    db.commit()
    db.refresh(document)

    create_audit_log(
        db=db,
        action="UPDATE_DOCUMENT_STATUS",
        resource_type="document",
        resource_id=document.id,
        details=f"Document status changed to {status}",
    )

    return {
        "message": "Document status updated",
        "document_id": document.id,
        "status": document.status,
    }


# ============================================================
# DELETE DOCUMENT
# ============================================================

@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    file_path = document.file_path

    if file_path and os.path.exists(file_path):
        os.remove(file_path)

    db.delete(document)
    db.commit()

    create_audit_log(
        db=db,
        action="DELETE_DOCUMENT",
        resource_type="document",
        resource_id=document_id,
        details=f"Document '{document.filename}' deleted",
    )

    return {
        "message": "Document deleted successfully",
        "document_id": document_id,
    }