from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.verify_log import VerifyLog


class VerifyLogRepository:
    async def get_by_user(
        self, db: AsyncSession, user_id: int, limit: int = 50
    ) -> list[VerifyLog]:
        result = await db.execute(
            select(VerifyLog)
            .filter(VerifyLog.verified_by_user_id == user_id)
            .order_by(desc(VerifyLog.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())


verify_log_repo = VerifyLogRepository()
