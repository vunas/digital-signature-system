from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.certificate import Certificate
    from app.models.document import Document
    from app.models.key import Key


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    keys: Mapped[List["Key"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    documents: Mapped[List["Document"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    certificates: Mapped[List["Certificate"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )

    def deactivate(self) -> None:
        """Khóa tài khoản người dùng"""
        self.is_active = False

    def activate(self) -> None:
        """Kích hoạt lại tài khoản"""
        self.is_active = True
