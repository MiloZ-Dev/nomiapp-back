import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Empresa(Base):
    __tablename__ = "empresas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    nit: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    ciudad: Mapped[str | None] = mapped_column(String(120))
    direccion: Mapped[str | None] = mapped_column(String(255))
    telefono: Mapped[str | None] = mapped_column(String(50))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    empleados: Mapped[list["Empleado"]] = relationship(  # noqa: F821
        back_populates="empresa", cascade="all, delete-orphan"
    )
