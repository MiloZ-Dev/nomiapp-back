import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class RolEnum(str, enum.Enum):
    super_admin = "super_admin"
    admin_empresa = "admin_empresa"


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[RolEnum] = mapped_column(
        SAEnum(RolEnum, name="rol_enum"),
        default=RolEnum.super_admin,
        nullable=False,
    )
    empresa_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("empresas.id", ondelete="CASCADE"),
        nullable=True,
        default=None,
        index=True,
    )
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
