from fastapi import APIRouter, UploadFile, File, HTTPException

from app.core.dependencies import CurrentUserDep, DatabaseDep
from app.schemas.verify_schema import VerifyResponse
from app.services.verify_service import verify_service
from app.utils.logger import logger

router = APIRouter(prefix="/api/verify", tags=["Verification"])


@router.post("/pdf", response_model=VerifyResponse)
async def verify_uploaded_pdf(
    db: DatabaseDep,
    current_user: CurrentUserDep,
    file: UploadFile = File(...),
):
    """
    Xác thực một file PDF xem đã được ký chưa, có bị chỉnh sửa không.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Vui lòng tải lên file định dạng PDF.")

    try:
        logger.info(
            f"User {current_user.username} đang thực hiện xác thực tài liệu PDF: {file.filename}"
        )
        return await verify_service.verify_pdf_signature(db, file, current_user.id)

    except Exception as e:
        logger.error(f"Lỗi hệ thống khi verify PDF ({file.filename}): {str(e)}")
        raise HTTPException(status_code=500, detail="Đã xảy ra lỗi trong quá trình phân tích file.")
