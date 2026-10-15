from fastapi import APIRouter, HTTPException, status

from app.core.dependencies import CurrentUserDep, DatabaseDep
from app.schemas.signature_schema import SignatureCreate, SignatureResponse
from app.services.sign_service import sign_service
from app.utils.logger import logger

router = APIRouter(prefix="/api/signatures", tags=["Signatures"])


@router.post("/sign-pdf", response_model=SignatureResponse)
async def sign_document(
    sign_data: SignatureCreate,
    db: DatabaseDep,
    current_user: CurrentUserDep,
):
    """Ký số lên tài liệu PDF bằng cách tương tác với hệ thống PKI nội bộ."""
    try:
        logger.info(
            f"User {current_user.username} đang thực hiện ký tài liệu ID {sign_data.document_id}"
        )

        signature_record = await sign_service.sign_pdf(db, current_user.id, sign_data)

        return signature_record

    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Lỗi ký tài liệu: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi ký tài liệu: {str(e)}",
        )
