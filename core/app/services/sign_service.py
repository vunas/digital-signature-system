import asyncio
import hashlib
import logging
import os
import tempfile
from datetime import datetime

import httpx
from asn1crypto import keys, pem, x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import signers
from pyhanko.sign.fields import SigSeedSubFilter
from pyhanko.sign.timestamps import HTTPTimeStamper
from pyhanko_certvalidator.registry import SimpleCertificateStore
from sqlalchemy.ext.asyncio import AsyncSession

# Centralized Enums
from app.models.enums import TargetResourceType
from app.repositories.certificate_repo import certificate_repo
from app.repositories.credential_repo import credential_repo
from app.repositories.key_repo import key_repo
from app.repositories.signature_repo import signature_repo
from app.schemas.signature_schema import SignatureCreate
from app.services.crypto.aes_service import aes_service
from app.services.log_service import log_service
from app.utils.file_utils import (
    get_file_content,
    get_signed_file_path,
    save_signed_file_content,
)


class SignService:
    async def sign_pdf(
        self,
        db: AsyncSession,
        tenant_id: int | None = None,
        user_id: int | SignatureCreate | None = None,
        sign_data: SignatureCreate | None = None,
    ):
        if sign_data is None:
            sign_data = user_id
            user_id = None
        """Thực hiện nhúng chữ ký số chuẩn PAdES vào tệp PDF (Bất đồng bộ)."""

        credential, key_record, cert_record = await self._get_and_validate_records(
            db, tenant_id, sign_data
        )

        input_db_path = getattr(credential, "file_download_url", None)
        if input_db_path is None:
            input_db_path = getattr(credential, "signed_file_path", None) or getattr(
                credential, "original_file_path", None
            )
        output_db_path = get_signed_file_path(
            credential.file_name or "credential.pdf", input_db_path
        )

        private_key = self._load_private_key(key_record, sign_data)
        end_entity_cert = self._load_certificate(cert_record)
        cert_registry = await self._build_certificate_registry(db)

        timestamper = await self._setup_timestamper()

        # Thực thi xử lý PDF nặng thông qua ThreadPool
        new_signed_hash = await asyncio.to_thread(
            self._execute_pdf_signing,
            input_db_path=input_db_path,
            output_db_path=output_db_path,
            private_key=private_key,
            end_entity_cert=end_entity_cert,
            cert_registry=cert_registry,
            timestamper=timestamper,
            sign_data=sign_data,
        )

        credential.mark_as_signed(new_signed_path=output_db_path, new_signed_hash=new_signed_hash)

        signature_record = await signature_repo.create(
            db=db,
            credential_id=credential.id,
            key_id=key_record.id,
            certificate_id=cert_record.id,
            user_id=user_id,
            signer_name=sign_data.signer_name,
            signer_reason=sign_data.signer_reason,
            signer_location=sign_data.signer_location,
            visible_signature=True,
        )

        await log_service.log_action(
            db=db,
            user_id=user_id,
            action="SIGN_DOCUMENT",
            target_type=TargetResourceType.SIGNATURE,
            target_id=str(signature_record.id),
            payload={"credential_id": credential.id, "signer_name": sign_data.signer_name},
        )

        return signature_record

    async def _get_and_validate_records(
        self,
        db: AsyncSession,
        tenant_id: int | None = None,
        sign_data: SignatureCreate | None = None,
        user_id: int | None = None,
    ):
        tenant_id = tenant_id if tenant_id is not None else user_id
        credential = await credential_repo.get_by_id(db, sign_data.credential_id, tenant_id)
        key_record = await key_repo.get_by_id(db, sign_data.key_id, tenant_id)

        cert_record = None
        if key_record:
            cert_record = await certificate_repo.get_by_key_id(db, key_record.id, tenant_id)

        if not credential or not key_record or not cert_record:
            raise ValueError(
                "Không tìm thấy tài liệu/credential, khóa hoặc chứng thư số tương ứng."
            )

        # Check tính hợp lệ của cert
        if not cert_record.is_valid_now():
            raise ValueError("Chứng chỉ không hợp lệ hoặc đã hết hạn.")

        return credential, key_record, cert_record

    def _load_private_key(self, key_record, sign_data: SignatureCreate):
        storage_type = getattr(key_record.storage_type, "value", key_record.storage_type)
        if storage_type == "local":
            if not getattr(sign_data, "raw_private_key", None):
                raise ValueError("Vui lòng đính kèm file Private Key (.pem) từ máy của bạn để ký.")
            priv_key_bytes = sign_data.raw_private_key.encode("utf-8")
        else:
            if getattr(sign_data, "passphrase", None):
                priv_key_bytes = key_record.private_key_encrypted
            else:
                priv_key_bytes = aes_service.decrypt_key(key_record.private_key_encrypted)

        try:
            password = (
                sign_data.passphrase.encode("utf-8")
                if getattr(sign_data, "passphrase", None)
                else None
            )
            crypto_priv_key = load_pem_private_key(priv_key_bytes, password=password)
        except Exception:
            raise ValueError("Mật khẩu giải mã khóa không hợp lệ hoặc sai định dạng khóa.")

        der_key_bytes = crypto_priv_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return keys.PrivateKeyInfo.load(der_key_bytes)

    def _load_certificate(self, cert_record):
        cert_bytes = getattr(cert_record, "certificate_data", None) or getattr(
            cert_record, "certificate_pem", None
        )
        if not cert_bytes:
            raise ValueError("Không tìm thấy dữ liệu chứng chỉ trong Database.")

        if isinstance(cert_bytes, str):
            cert_bytes = cert_bytes.encode("utf-8")
        if pem.detect(cert_bytes):
            _, _, der_cert_bytes = pem.unarmor(cert_bytes)
            return x509.Certificate.load(der_cert_bytes)
        return x509.Certificate.load(cert_bytes)

    async def _build_certificate_registry(self, db: AsyncSession):
        cert_registry = SimpleCertificateStore()
        inter_cert_record = await certificate_repo.get_by_name(db, "SecureSign Intermediate CA")

        if inter_cert_record:
            inter_cert_bytes = getattr(inter_cert_record, "certificate_data", None) or getattr(
                inter_cert_record, "certificate_pem", None
            )
            if inter_cert_bytes:
                if isinstance(inter_cert_bytes, str):
                    inter_cert_bytes = inter_cert_bytes.encode("utf-8")
                if pem.detect(inter_cert_bytes):
                    _, _, der_inter_bytes = pem.unarmor(inter_cert_bytes)
                    inter_cert = x509.Certificate.load(der_inter_bytes)
                else:
                    inter_cert = x509.Certificate.load(inter_cert_bytes)
                cert_registry.register(inter_cert)
        return cert_registry

    async def _setup_timestamper(self):
        tsa_url = os.getenv("TSA_URL")
        if not tsa_url:
            return None
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                await client.get(tsa_url)
            return HTTPTimeStamper(tsa_url)
        except (httpx.TimeoutException, httpx.RequestError, ValueError) as e:
            logging.warning(f"External TSA không phản hồi: {e}")
            return None

    def _execute_pdf_signing(
        self,
        input_db_path,
        output_db_path,
        private_key,
        end_entity_cert,
        cert_registry,
        timestamper,
        sign_data: SignatureCreate,
    ) -> str:
        """Thực hiện ký và trả về mã băm file mới."""
        tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        new_hash = None

        try:
            file_bytes = get_file_content(input_db_path)
            tmp_in.write(file_bytes)
            tmp_in.flush()

            signer = signers.SimpleSigner(
                signing_cert=end_entity_cert, signing_key=private_key, cert_registry=cert_registry
            )

            with open(tmp_in.name, "rb") as input_file:
                pdf_writer = IncrementalPdfFileWriter(input_file, strict=False)
                new_sig_field_name = f"Sig_{datetime.now().strftime('%Y%m%d%H%M%S')}"

                meta = signers.PdfSignatureMetadata(
                    field_name=new_sig_field_name,
                    location=sign_data.signer_location,
                    reason=sign_data.signer_reason,
                    name=sign_data.signer_name,
                    subfilter=SigSeedSubFilter.PADES,
                    embed_validation_info=False,
                )

                with open(tmp_out.name, "wb") as output_file:
                    try:
                        signers.sign_pdf(
                            pdf_writer,
                            meta,
                            signer=signer,
                            timestamper=timestamper,
                            existing_fields_only=False,
                            in_place=False,
                            output=output_file,
                        )
                    except Exception as e:
                        if timestamper:
                            input_file.seek(0)
                            pdf_writer = IncrementalPdfFileWriter(input_file, strict=False)
                            signers.sign_pdf(
                                pdf_writer,
                                meta,
                                signer=signer,
                                timestamper=None,
                                existing_fields_only=False,
                                in_place=False,
                                output=output_file,
                            )
                        else:
                            raise e

            with open(tmp_out.name, "rb") as f:
                signed_content = f.read()
                save_signed_file_content(output_db_path, signed_content)
                new_hash = hashlib.sha256(signed_content).hexdigest()

        finally:
            tmp_in.close()
            tmp_out.close()
            if os.path.exists(tmp_in.name):
                os.remove(tmp_in.name)
            if os.path.exists(tmp_out.name):
                os.remove(tmp_out.name)

        return new_hash


sign_service = SignService()
