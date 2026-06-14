import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.nomina import EstadoNominaEnum


class NominaGenerar(BaseModel):
    periodo_inicio: date
    periodo_fin: date

    @model_validator(mode="after")
    def validar_periodo(self):
        if self.periodo_fin < self.periodo_inicio:
            raise ValueError("periodo_fin no puede ser anterior a periodo_inicio")
        return self


class NominaDetalleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    empleado_id: uuid.UUID
    empleado_nombre: str = ""  # ← agregar esto
    salario_base: Decimal
    dias_trabajados: int
    horas_extra: Decimal
    valor_horas_extra: Decimal
    auxilio_transporte: Decimal
    salud_empleado: Decimal
    pension_empleado: Decimal
    total_deducciones: Decimal
    total_devengado: Decimal
    neto_pagado: Decimal


class NominaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    empresa_id: uuid.UUID
    periodo_inicio: date
    periodo_fin: date
    estado: EstadoNominaEnum
    total_devengado: Decimal
    total_deducciones: Decimal
    total_neto: Decimal
    created_at: datetime


class NominaDetalladaOut(NominaOut):
    detalles: list[NominaDetalleOut] = []
