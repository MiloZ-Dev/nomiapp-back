import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class EstadoNominaEnum(str, enum.Enum):
    borrador = "borrador"
    cerrada = "cerrada"


class Nomina(Base):
    __tablename__ = "nominas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    empresa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("empresas.id", ondelete="CASCADE"), index=True, nullable=False
    )
    periodo_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_fin: Mapped[date] = mapped_column(Date, nullable=False)
    estado: Mapped[EstadoNominaEnum] = mapped_column(
        SAEnum(EstadoNominaEnum, name="estado_nomina_enum"),
        default=EstadoNominaEnum.borrador,
        nullable=False,
    )
    total_devengado: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    total_deducciones: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    total_neto: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    detalles: Mapped[list["NominaDetalle"]] = relationship(
        back_populates="nomina",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class NominaDetalle(Base):
    __tablename__ = "nomina_detalles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nomina_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("nominas.id", ondelete="CASCADE"), index=True, nullable=False
    )
    empleado_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("empleados.id", ondelete="CASCADE"), index=True, nullable=False
    )
    salario_base: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    dias_trabajados: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    horas_extra: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), default=Decimal("0.00"), nullable=False
    )
    valor_horas_extra: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    auxilio_transporte: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    salud_empleado: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    pension_empleado: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_deducciones: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_devengado: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    neto_pagado: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    nomina: Mapped["Nomina"] = relationship(back_populates="detalles")
