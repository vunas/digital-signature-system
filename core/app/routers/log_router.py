from typing import List

from fastapi import APIRouter

from app.core.dependencies import CurrentUserDep, DatabaseDep
from app.repositories.audit_log_repo import audit_log_repo
from app.repositories.verify_log_repo import verify_log_repo
from app.schemas.log_schema import AuditLogResponse, VerifyLogResponse

router = APIRouter(prefix="/api/logs", tags=["Logs"])


@router.get("/audit", response_model=List[AuditLogResponse])
async def get_audit_logs(
    db: DatabaseDep,
    current_user: CurrentUserDep,
    limit: int = 50,
):
    """Lấy danh sách Audit Logs (vết hệ thống)."""
    return await audit_log_repo.get_by_user(db, current_user.id, limit)


@router.get("/verify", response_model=List[VerifyLogResponse])
async def get_verify_logs(
    db: DatabaseDep,
    current_user: CurrentUserDep,
    limit: int = 50,
):
    """Lấy lịch sử xác thực văn bản của User hiện tại."""
    return await verify_log_repo.get_by_user(db, current_user.id, limit)
