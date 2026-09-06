from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ============================================================
# USER SCHEMAS
# ============================================================

class UserCreate(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    role: str = "user"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# PROJECT SCHEMAS
# ============================================================

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    owner_id: int


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: str
    owner_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# DOCUMENT SCHEMAS
# ============================================================

class DocumentResponse(BaseModel):
    id: int
    project_id: int
    filename: str
    file_path: str
    file_type: Optional[str]
    file_size: Optional[int]
    status: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# AGENT TASK SCHEMAS
# ============================================================

class TaskCreate(BaseModel):
    project_id: int
    document_id: Optional[int] = None
    task_type: str
    description: Optional[str] = None
    selected_model: Optional[str] = None


class TaskUpdate(BaseModel):
    status: Optional[str] = None
    selected_model: Optional[str] = None
    result: Optional[str] = None
    error_message: Optional[str] = None


class TaskResponse(BaseModel):
    id: int
    project_id: int
    document_id: Optional[int]
    task_type: str
    description: Optional[str]
    status: str
    selected_model: Optional[str]
    result: Optional[str]
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# REPORT SCHEMAS
# ============================================================

class ReportCreate(BaseModel):
    project_id: int
    task_id: Optional[int] = None
    report_name: str
    report_type: str
    file_path: str


class ReportResponse(BaseModel):
    id: int
    project_id: int
    task_id: Optional[int]
    report_name: str
    report_type: str
    file_path: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)