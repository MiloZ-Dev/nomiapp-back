import uuid

from fastapi import APIRouter, status

from app.api.responses import envelope
from app.core.dependencies import DbSession, RequireEmpresaAccess, RequireSuperAdmin
from app.schemas.empresa import EmpresaCreate, EmpresaOut, EmpresaUpdate
from app.services import empresa_service

router = APIRouter(prefix="/empresas", tags=["empresas"])


@router.get("/")
async def listar(db: DbSession, _: RequireSuperAdmin, incluir_inactivas: bool = False):
    empresas = await empresa_service.list_empresas(db, incluir_inactivas)
    return envelope(
        data=[EmpresaOut.model_validate(e) for e in empresas],
        message="Empresas listadas",
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def crear(payload: EmpresaCreate, db: DbSession, _: RequireSuperAdmin):
    resultado = await empresa_service.create_empresa(db, payload)
    return envelope(
        data={
            "empresa": EmpresaOut.model_validate(resultado["empresa"]),
            "credenciales": resultado["credenciales"],
        },
        message="Empresa creada con usuario administrador",
    )


@router.get("/{empresa_id}")
async def obtener(empresa_id: uuid.UUID, db: DbSession, _: RequireEmpresaAccess):
    empresa = await empresa_service.get_empresa(db, empresa_id)
    return envelope(
        data=EmpresaOut.model_validate(empresa), message="Empresa encontrada"
    )


@router.put("/{empresa_id}")
async def actualizar(
    empresa_id: uuid.UUID, payload: EmpresaUpdate, db: DbSession, _: RequireEmpresaAccess
):
    empresa = await empresa_service.update_empresa(db, empresa_id, payload)
    return envelope(
        data=EmpresaOut.model_validate(empresa), message="Empresa actualizada"
    )


@router.delete("/{empresa_id}")
async def eliminar(empresa_id: uuid.UUID, db: DbSession, _: RequireSuperAdmin):
    empresa = await empresa_service.soft_delete_empresa(db, empresa_id)
    return envelope(
        data=EmpresaOut.model_validate(empresa),
        message="Empresa desactivada (soft delete)",
    )
