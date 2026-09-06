from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import User
from app.schemas.schemas import UserCreate, UserResponse
from app.services.audit_service import create_audit_log


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


# ============================================================
# CREATE USER
# ============================================================

@router.post("/", response_model=UserResponse)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    existing_user = (
        db.query(User)
        .filter(
            (User.username == user_data.username)
            | (User.email == user_data.email)
        )
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username or email already exists",
        )

    user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    create_audit_log(
        db=db,
        action="CREATE_USER",
        resource_type="user",
        resource_id=user.id,
        user_id=user.id,
        details=f"User {user.username} created",
    )

    return user


# ============================================================
# GET ALL USERS
# ============================================================

@router.get("/", response_model=list[UserResponse])
def get_users(
    db: Session = Depends(get_db),
):
    return (
        db.query(User)
        .order_by(User.created_at.desc())
        .all()
    )


# ============================================================
# GET USER
# ============================================================

@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return user


# ============================================================
# ACTIVATE / DEACTIVATE USER
# ============================================================

@router.patch("/{user_id}/status")
def change_user_status(
    user_id: int,
    active: bool,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    user.is_active = active

    db.commit()
    db.refresh(user)

    create_audit_log(
        db=db,
        action="CHANGE_USER_STATUS",
        resource_type="user",
        resource_id=user.id,
        user_id=user.id,
        details=f"User active status changed to {active}",
    )

    return {
        "message": "User status updated",
        "user_id": user.id,
        "is_active": user.is_active,
    }