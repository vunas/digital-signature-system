from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.user import User


async def seed_users(db: AsyncSession):
    print("👤 Đang tạo Users...")

    users_data = [
        {"username": "admin", "pass": "123456"},
        {"username": "giamdoc", "pass": "123456"},
        {"username": "nhanvien", "pass": "123456"},
        {"username": "demo", "pass": "123456"},
        {"username": "user1", "pass": "123456"},
        {"username": "user2", "pass": "123456"},
        {"username": "user3", "pass": "123456"},
        {"username": "user4", "pass": "123456"},
        {"username": "user5", "pass": "123456"},
        {"username": "user6", "pass": "123456"},
        {"username": "user7", "pass": "123456"},
        {"username": "user8", "pass": "123456"},
        {"username": "user9", "pass": "123456"},
        {"username": "user0", "pass": "123456"},
    ]

    created_users = {}

    for user_data in users_data:
        user = User(
            username=user_data["username"],
            password_hash=get_password_hash(user_data["pass"]),
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        created_users[user.username] = user
        print(f"  -> Đã tạo user: {user.username}")

    return created_users
