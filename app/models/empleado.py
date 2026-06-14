import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Empleado(Base):
    __tablename__ = "empleados"
    __table_args__ = (
        UniqueConstraint("empresa_id", "cedula", name="uq_empleado_empresa_cedula"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("empresas.id", ondelete="CASCADE"), index=True, nullable=False
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    apellido: Mapped[str] = mapped_column(String(120), nullable=False)
    cedula: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    telefono: Mapped[str | None] = mapped_column(String(50))
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date)
    cargo: Mapped[str | None] = mapped_column(String(120))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    empresa: Mapped["Empresa"] = relationship(back_populates="empleados")  # noqa: F821
    contrato: Mapped["Contrato | None"] = relationship(  # noqa: F821
        back_populates="empleado",
        uselist=False,
        cascade="all, delete-orphan",
    )
