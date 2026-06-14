import uuid

from fastapi import APIRouter, status

from app.api.responses import envelope
from app.core.dependencies import DbSession, RequireEmpresaAccess
from app.schemas.empleado import (
    ContratoCreate,
    ContratoOut,
    EmpleadoCreate,
    EmpleadoOut,
    EmpleadoUpdate,
)
from app.services import empleado_service

router = APIRouter(prefix="/empresas/{empresa_id}/empleados", tags=["empleados"])


@router.get("/")
async def listar(
    empresa_id: uuid.UUID,
    db: DbSession,
    _: RequireEmpresaAccess,
    incluir_inactivos: bool = False,
):
    empleados = await empleado_service.list_empleados(db, empresa_id, incluir_inactivos)
    return envelope(
        data=[EmpleadoOut.model_validate(e) for e in empleados],
        message="Empleados listados",
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def crear(
    empresa_id: uuid.UUID, payload: EmpleadoCreate, db: DbSession, _: RequireEmpresaAccess
):
    empleado = await empleado_service.create_empleado(db, empresa_id, payload)
    return envelope(
        data=EmpleadoOut.model_validate(empleado), message="Empleado creado"
    )


@router.get("/{empleado_id}")
async def obtener(
    empresa_id: uuid.UUID, empleado_id: uuid.UUID, db: DbSession, _: RequireEmpresaAccess
):
    empleado = await empleado_service.get_empleado(db, empresa_id, empleado_id)
    return envelope(
        data=EmpleadoOut.model_validate(empleado), message="Empleado encontrado"
    )


@router.put("/{empleado_id}")
async def actualizar(
    empresa_id: uuid.UUID,
    empleado_id: uuid.UUID,
    payload: EmpleadoUpdate,
    db: DbSession,
    _: RequireEmpresaAccess,
):
    empleado = await empleado_service.update_empleado(
        db, empresa_id, empleado_id, payload
    )
    return envelope(
        data=EmpleadoOut.model_validate(empleado), message="Empleado actualizado"
    )


@router.post("/{empleado_id}/contrato")
async def upsert_contrato(
    empresa_id: uuid.UUID,
    empleado_id: uuid.UUID,
    payload: ContratoCreate,
    db: DbSession,
    _: RequireEmpresaAccess,
):
    contrato = await empleado_service.upsert_contrato(
        db, empresa_id, empleado_id, payload
    )
    return envelope(
        data=ContratoOut.model_validate(contrato),
        message="Contrato guardado",
    )
