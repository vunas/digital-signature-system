from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.enums import TenantStatus, UserRole
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.user_schema import UserCreate


class UserRepository:
    async def get_by_username(self, db: AsyncSession, username: str):
        stmt = select(User).where(User.username == username)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, db: AsyncSession, user_id: int):
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, obj_in: UserCreate):
        hashed_password = get_password_hash(obj_in.password)
        tenant_result = await db.execute(
            select(Tenant).where(Tenant.status == TenantStatus.ACTIVE).limit(1)
        )
        tenant = tenant_result.scalar_one_or_none()
        if tenant is None:
            raise ValueError("Chưa có tenant ACTIVE để tạo tài khoản.")
        db_obj = User(
            username=obj_in.username,
            password_hash=hashed_password,
            tenant_id=tenant.id,
            role=UserRole.TENANT_OPERATOR,
        )
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj


user_repo = UserRepository()
