from sqlalchemy.orm import Session

from app.database.models import AuditLog


def create_audit_log(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: int | None = None,
    user_id: int | None = None,
    details: str | None = None,
    success: bool = True,
):
    """
    Centralized audit logging service.

    Used by Projects, Documents, Tasks, Reports and
    other backend modules.
    """

    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        success=success,
    )

    db.add(log)
    db.commit()

    return log