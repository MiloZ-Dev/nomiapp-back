import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EmpresaBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=255)
    nit: str = Field(..., min_length=1, max_length=50)
    ciudad: str | None = None
    direccion: str | None = None
    telefono: str | None = None


class EmpresaCreate(EmpresaBase):
    pass


class EmpresaUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=255)
    nit: str | None = Field(None, min_length=1, max_length=50)
    ciudad: str | None = None
    direccion: str | None = None
    telefono: str | None = None
    activo: bool | None = None


class EmpresaOut(EmpresaBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    activo: bool
    created_at: datetime
