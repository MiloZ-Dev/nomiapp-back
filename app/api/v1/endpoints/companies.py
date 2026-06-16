import uuid

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.api.responses import envelope
from app.core.dependencies import DbSession, RequireCompanyAccess, RequireSuperAdmin
from app.schemas.company import CompanyCreate, CompanyOut, CompanyUpdate
from app.services import company_service, storage_service

router = APIRouter(prefix="/empresas", tags=["companies"])

ALLOWED_LOGO_TYPES = {"image/jpeg", "image/png"}
MAX_LOGO_SIZE = 2 * 1024 * 1024  # 2 MB


@router.get("/")
async def list_all(
    db: DbSession,
    _: RequireSuperAdmin,
    include_inactive: bool = Query(False, alias="incluir_inactivas"),
):
    companies = await company_service.list_companies(db, include_inactive)
    return envelope(
        data=[CompanyOut.model_validate(c) for c in companies],
        message="Empresas listadas",
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create(payload: CompanyCreate, db: DbSession, _: RequireSuperAdmin):
    result = await company_service.create_company(db, payload)
    return envelope(
        data={
            "empresa": CompanyOut.model_validate(result["company"]),
            "credenciales": result["credentials"],
        },
        message="Empresa creada con usuario administrador",
    )


@router.get("/{company_id}")
async def get(company_id: uuid.UUID, db: DbSession, _: RequireCompanyAccess):
    company = await company_service.get_company(db, company_id)
    return envelope(
        data=CompanyOut.model_validate(company), message="Empresa encontrada"
    )


@router.put("/{company_id}")
async def update(
    company_id: uuid.UUID, payload: CompanyUpdate, db: DbSession, _: RequireSuperAdmin
):
    company = await company_service.update_company(db, company_id, payload)
    return envelope(
        data=CompanyOut.model_validate(company), message="Empresa actualizada"
    )


@router.post("/{company_id}/logo")
async def upload_logo(
    company_id: uuid.UUID,
    db: DbSession,
    _: RequireSuperAdmin,
    file: UploadFile = File(...),
):
    if file.content_type not in ALLOWED_LOGO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Tipo de archivo no permitido. Use image/jpeg o image/png.",
        )

    # Verify the company exists before uploading anything to storage.
    await company_service.get_company(db, company_id)

    file_bytes = await file.read()
    if len(file_bytes) > MAX_LOGO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El logo no puede superar los 2 MB.",
        )
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo está vacío.",
        )

    logo_url = await storage_service.upload_logo(
        str(company_id), file_bytes, file.content_type
    )
    company = await company_service.set_logo_url(db, company_id, logo_url)

    return envelope(
        data=CompanyOut.model_validate(company),
        message="Logo actualizado",
    )


@router.delete("/{company_id}")
async def delete(company_id: uuid.UUID, db: DbSession, _: RequireSuperAdmin):
    company = await company_service.soft_delete_company(db, company_id)
    return envelope(
        data=CompanyOut.model_validate(company),
        message="Empresa desactivada (soft delete)",
    )
