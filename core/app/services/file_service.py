import hashlib
import uuid
from datetime import date

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TargetResourceType
from app.repositories.credential_repo import credential_repo
from app.services.log_service import log_service
from app.utils.file_utils import save_file


class FileService:
    async def upload_credential(
        self,
        db: AsyncSession,
        user_id: int,
        file: UploadFile,
        tenant_id: int | None = None,
    ):
        tenant_id = tenant_id if tenant_id is not None else user_id
        content = await file.read()

        safe_filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"

        original_hash = hashlib.sha256(content).hexdigest()

        saved_path = await save_file(
            content=content, filename=safe_filename, content_type=file.content_type
        )

        credential = await credential_repo.create(
            db=db,
            tenant_id=tenant_id,
            created_by_user_id=user_id,
            tracking_id=uuid.uuid4().hex,
            student_name="Chưa cập nhật",
            student_id=f"TEMP-{uuid.uuid4().hex[:12]}",
            issue_date=date.today(),
            file_name=file.filename,
            file_download_url=saved_path,
            original_hash=original_hash,
            signed_hash=original_hash,
        )

        await log_service.log_action(
            db=db,
            user_id=user_id,
            action="UPLOAD_CREDENTIAL",
            target_type=TargetResourceType.CREDENTIAL,
            target_id=str(credential.id),
            payload={"file_name": file.filename, "original_hash": original_hash},
        )

        return credential


file_service = FileService()
