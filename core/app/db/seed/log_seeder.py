import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signature import Signature
from app.models.verify_log import VerifyLog


async def seed_logs(db: AsyncSession, docs: list):
    print("📊 Đang tạo Logs...")

    result = await db.execute(select(Signature))
    signatures = result.scalars().all()
    if not signatures:
        print("⚠️ Không có signature nào")
        return

    verified_docs = [doc for doc in docs if doc.status == "VERIFIED"]
    for doc in verified_docs:
        db.add(
            VerifyLog(
                document_id=doc.id,
                signature_id=random.choice(signatures).id,
                is_valid=True,
                message="Chữ ký hợp lệ",
                created_at=datetime.now(UTC)
                - timedelta(hours=random.randint(1, 48)),
            )
        )

    await db.commit()
    print("  -> Đã tạo Verify Logs")
