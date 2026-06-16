import uuid

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.api.responses import envelope
from app.core.dependencies import DbSession, RequireCompanyAccess
from app.schemas.employee import (
    ContractCreate,
    ContractOut,
    EmployeeCreate,
    EmployeeDetailedOut,
    EmployeeOut,
    EmployeeUpdate,
)
from app.schemas.incident import IncidentCreate, IncidentOut
from app.services import ai_service, employee_service, incident_service, storage_service

router = APIRouter(prefix="/empresas/{company_id}/empleados", tags=["employees"])

ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png"}
MAX_PHOTO_SIZE = 2 * 1024 * 1024  # 2 MB
MAX_CONTRACT_SIZE = 10 * 1024 * 1024  # 10 MB


@router.get("/")
async def list_all(
    company_id: uuid.UUID,
    db: DbSession,
    _: RequireCompanyAccess,
    include_inactive: bool = Query(False, alias="incluir_inactivos"),
):
    employees = await employee_service.list_employees(db, company_id, include_inactive)
    return envelope(
        data=[EmployeeOut.model_validate(e) for e in employees],
        message="Empleados listados",
    )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create(
    company_id: uuid.UUID, payload: EmployeeCreate, db: DbSession, _: RequireCompanyAccess
):
    employee = await employee_service.create_employee(db, company_id, payload)
    return envelope(
        data=EmployeeOut.model_validate(employee), message="Empleado creado"
    )


@router.post("/extraer-contrato")
async def extract_contract(
    company_id: uuid.UUID,
    db: DbSession,
    _: RequireCompanyAccess,
    file: UploadFile = File(...),
):
    """Receives a contract PDF and returns the data extracted by AI.

    If AI is not available (no ANTHROPIC_API_KEY) it returns an empty structure
    to fill in manually. The file is NOT stored: it is only analyzed.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Solo se aceptan archivos PDF",
        )

    content = await file.read()
    if len(content) > MAX_CONTRACT_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El archivo no puede superar 10MB",
        )

    text = await ai_service.extract_pdf_text(content)
    result = await ai_service.extract_contract_data(text)

    return envelope(
        data=result,
        message=(
            "Extracción completada"
            if result.get("ai_available")
            else "AI no disponible"
        ),
    )


@router.get("/{employee_id}")
async def get(
    company_id: uuid.UUID, employee_id: uuid.UUID, db: DbSession, _: RequireCompanyAccess
):
    employee = await employee_service.get_employee(db, company_id, employee_id)
    return envelope(
        data=EmployeeOut.model_validate(employee), message="Empleado encontrado"
    )


@router.get("/{employee_id}/detallado")
async def get_detailed(
    company_id: uuid.UUID, employee_id: uuid.UUID, db: DbSession, _: RequireCompanyAccess
):
    employee = await employee_service.get_employee_detailed(
        db, company_id, employee_id
    )
    return envelope(
        data=EmployeeDetailedOut.model_validate(employee),
        message="Empleado encontrado",
    )


@router.put("/{employee_id}")
async def update(
    company_id: uuid.UUID,
    employee_id: uuid.UUID,
    payload: EmployeeUpdate,
    db: DbSession,
    _: RequireCompanyAccess,
):
    employee = await employee_service.update_employee(
        db, company_id, employee_id, payload
    )
    return envelope(
        data=EmployeeOut.model_validate(employee), message="Empleado actualizado"
    )


@router.post("/{employee_id}/contrato")
async def upsert_contract(
    company_id: uuid.UUID,
    employee_id: uuid.UUID,
    payload: ContractCreate,
    db: DbSession,
    _: RequireCompanyAccess,
):
    contract = await employee_service.upsert_contract(
        db, company_id, employee_id, payload
    )
    return envelope(
        data=ContractOut.model_validate(contract),
        message="Contrato guardado",
    )


# --------------------------------------------------------------------------- #
# Incidents
# --------------------------------------------------------------------------- #
@router.post("/{employee_id}/novedades", status_code=status.HTTP_201_CREATED)
async def create_incident(
    company_id: uuid.UUID,
    employee_id: uuid.UUID,
    payload: IncidentCreate,
    db: DbSession,
    current: RequireCompanyAccess,
):
    incident = await incident_service.create_incident(
        db, company_id, employee_id, payload, created_by=current.id
    )
    return envelope(
        data=IncidentOut.model_validate(incident), message="Novedad creada"
    )


@router.get("/{employee_id}/novedades")
async def list_incidents(
    company_id: uuid.UUID,
    employee_id: uuid.UUID,
    db: DbSession,
    _: RequireCompanyAccess,
    applied: bool | None = Query(False, alias="aplicada"),
    month: str | None = Query(None, alias="mes"),
):
    incidents = await incident_service.list_incidents(
        db, company_id, employee_id, applied=applied, month=month
    )
    return envelope(
        data=[IncidentOut.model_validate(i) for i in incidents],
        message="Novedades listadas",
    )


@router.delete("/{employee_id}/novedades/{incident_id}")
async def delete_incident(
    company_id: uuid.UUID,
    employee_id: uuid.UUID,
    incident_id: uuid.UUID,
    db: DbSession,
    _: RequireCompanyAccess,
):
    await incident_service.delete_incident(db, company_id, employee_id, incident_id)
    return envelope(data=None, message="Novedad eliminada")


# --------------------------------------------------------------------------- #
# Employee documents (photo / contract PDF)
# --------------------------------------------------------------------------- #
@router.post("/{employee_id}/foto")
async def upload_photo(
    company_id: uuid.UUID,
    employee_id: uuid.UUID,
    db: DbSession,
    _: RequireCompanyAccess,
    file: UploadFile = File(...),
):
    if file.content_type not in ALLOWED_PHOTO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Tipo de archivo no permitido. Use image/jpeg o image/png.",
        )

    # Verify the employee exists before uploading anything to storage.
    await employee_service.get_employee(db, company_id, employee_id)

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="El archivo está vacío."
        )
    if len(file_bytes) > MAX_PHOTO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="La foto no puede superar los 2 MB.",
        )

    photo_url = await storage_service.upload_employee_photo(
        str(company_id), str(employee_id), file_bytes, file.content_type
    )
    employee = await employee_service.set_photo_url(
        db, company_id, employee_id, photo_url
    )
    return envelope(
        data=EmployeeOut.model_validate(employee), message="Foto actualizada"
    )


@router.post("/{employee_id}/contrato-pdf")
async def upload_contract_pdf(
    company_id: uuid.UUID,
    employee_id: uuid.UUID,
    db: DbSession,
    _: RequireCompanyAccess,
    file: UploadFile = File(...),
):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Tipo de archivo no permitido. Use application/pdf.",
        )

    await employee_service.get_employee(db, company_id, employee_id)

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="El archivo está vacío."
        )
    if len(file_bytes) > MAX_CONTRACT_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El contrato no puede superar los 10 MB.",
        )

    contract_url = await storage_service.upload_employee_contract(
        str(company_id), str(employee_id), file_bytes
    )
    employee = await employee_service.set_contract_url(
        db, company_id, employee_id, contract_url
    )
    # FUTURE: trigger AI contract extraction (for now it is only stored).
    return envelope(
        data=EmployeeOut.model_validate(employee), message="Contrato PDF actualizado"
    )
