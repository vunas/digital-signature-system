from unittest.mock import AsyncMock

import pytest

pytestmark = pytest.mark.asyncio


@pytest.mark.integration
async def test_verify_endpoint_rejects_non_pdf(client_full, override_current_user_full):
    # Validates: content-type gate rejects non-PDF uploads.
    res = await client_full.post(
        "/api/verify/pdf",
        files={"file": ("x.txt", b"hi", "text/plain")},
    )
    assert res.status_code == 400


@pytest.mark.integration
async def test_verify_endpoint_calls_service_and_returns_payload(
    monkeypatch, client_full, override_current_user_full
):
    # Validates: route delegates the upload stream to VerifyService.
    monkeypatch.setattr(
        "app.routers.verify_router.verify_service.verify_pdf_signature",
        AsyncMock(return_value={"is_valid": False, "message": "invalid", "signer_info": None}),
    )

    res = await client_full.post(
        "/api/verify/pdf",
        files={"file": ("doc.pdf", b"%PDF-1.4\n%", "application/pdf")},
    )
    assert res.status_code == 200, res.text
    assert res.json()["message"] == "invalid"
