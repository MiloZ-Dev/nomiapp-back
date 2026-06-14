import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.contrato import TipoContratoEnum


# --------------------------------------------------------------------------- #
# Empleado
# --------------------------------------------------------------------------- #
class EmpleadoBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=120)
    apellido: str = Field(..., min_length=1, max_length=120)
    cedula: str = Field(..., min_length=1, max_length=50)
    email: EmailStr | None = None
    telefono: str | None = None
    fecha_nacimiento: date | None = None
    cargo: str | None = None


class EmpleadoCreate(EmpleadoBase):
    pass


class EmpleadoUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=120)
    apellido: str | None = Field(None, min_length=1, max_length=120)
    cedula: str | None = Field(None, min_length=1, max_length=50)
    email: EmailStr | None = None
    telefono: str | None = None
    fecha_nacimiento: date | None = None
    cargo: str | None = None
    activo: bool | None = None


# --------------------------------------------------------------------------- #
# Contrato
# --------------------------------------------------------------------------- #
class ContratoBase(BaseModel):
    tipo: TipoContratoEnum
    salario_base: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    fecha_inicio: date
    fecha_fin: date | None = None
    eps: str | None = None
    afp: str | None = None
    arl: str | None = None
    caja_compensacion: str | None = None


class ContratoCreate(ContratoBase):
    pass


class ContratoOut(ContratoBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    empleado_id: uuid.UUID
    activo: bool
    created_at: datetime


class EmpleadoOut(EmpleadoBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    empresa_id: uuid.UUID
    activo: bool
    created_at: datetime
    contrato: ContratoOut | None = None
