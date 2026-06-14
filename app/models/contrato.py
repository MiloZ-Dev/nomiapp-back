import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class TipoContratoEnum(str, enum.Enum):
    termino_fijo = "termino_fijo"
    indefinido = "indefinido"
    obra_labor = "obra_labor"


class Contrato(Base):
    __tablename__ = "contratos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    empleado_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("empleados.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    tipo: Mapped[TipoContratoEnum] = mapped_column(
        SAEnum(TipoContratoEnum, name="tipo_contrato_enum"), nullable=False
    )
    salario_base: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date | None] = mapped_column(Date)
    eps: Mapped[str | None] = mapped_column(String(120))
    afp: Mapped[str | None] = mapped_column(String(120))
    arl: Mapped[str | None] = mapped_column(String(120))
    caja_compensacion: Mapped[str | None] = mapped_column(String(120))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    empleado: Mapped["Empleado"] = relationship(back_populates="contrato")  # noqa: F821
