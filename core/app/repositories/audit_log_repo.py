from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditLogRepository:
    async def get_by_user(
        self, db: AsyncSession, user_id: int, limit: int = 50
    ) -> list[AuditLog]:
        result = await db.execute(
            select(AuditLog)
            .filter(AuditLog.user_id == user_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())


audit_log_repo = AuditLogRepository()
