import hashlib
import os

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


async def seed_documents(db: AsyncSession, users: dict):
    print("📄 Đang tạo Documents...")

    upload_dir = "storage/uploads"
    os.makedirs(upload_dir, exist_ok=True)

    docs_info = [
        {
            "name": "hop_dong_thue_nha_2026.pdf",
            "user_id": users["giamdoc"].id,
            "status": "SIGNED",
        },
        {
            "name": "don_xin_nghi_phep_T4.pdf",
            "user_id": users["nhanvien"].id,
            "status": "UPLOADED",
        },
        {
            "name": "bao_cao_tai_chinh_Q1.pdf",
            "user_id": users["giamdoc"].id,
            "status": "VERIFIED",
        },
    ]
    minimal_pdf = b"%PDF-1.4 fake"
    created_docs = []

    for doc_data in docs_info:
        file_hash = hashlib.sha256(minimal_pdf + doc_data["name"].encode()).hexdigest()
        file_path = os.path.join(upload_dir, doc_data["name"])

        with open(file_path, "wb") as file:
            file.write(minimal_pdf)

        new_doc = Document(
            user_id=doc_data["user_id"],
            file_name=doc_data["name"],
            original_file_path=file_path,
            signed_file_path=(file_path if doc_data["status"] != "UPLOADED" else None),
            file_size=len(minimal_pdf),
            mime_type="application/pdf",
            file_hash=file_hash,
            signed_file_hash=(file_hash if doc_data["status"] != "UPLOADED" else None),
            status=doc_data["status"],
        )
        db.add(new_doc)
        created_docs.append(new_doc)

    await db.commit()
    for doc in created_docs:
        await db.refresh(doc)

    print(f"  -> Đã tạo {len(created_docs)} tài liệu")
    return created_docs
