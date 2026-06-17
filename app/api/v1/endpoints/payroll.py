import re
import uuid
from io import BytesIO

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse

from app.api.responses import envelope
from app.core.dependencies import DbSession, RequireCompanyAccess
from app.schemas.payroll import (
    PayrollDetailedOut,
    PayrollDetailUpdate,
    PayrollGenerate,
    PayrollOut,
    PayrollPendingOut,
)
from app.services import payroll_service, pdf_service

router = APIRouter(prefix="/empresas/{company_id}/nomina", tags=["payroll"])


def _slug_filename(text: str) -> str:
    """Normalizes a text to use it as a file name."""
    s = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return s or "archivo"


@router.post("/generar", status_code=status.HTTP_201_CREATED)
async def generate(
    company_id: uuid.UUID, payload: PayrollGenerate, db: DbSession, _: RequireCompanyAccess
):
    payroll = await payroll_service.generate_payroll(db, company_id, payload)
    return envelope(
        data=PayrollDetailedOut.model_validate(payroll),
        message="Nómina generada en estado borrador",
    )


@router.get("/")
async def list_all(company_id: uuid.UUID, db: DbSession, _: RequireCompanyAccess):
    payrolls = await payroll_service.list_payrolls(db, company_id)
    return envelope(
        data=[PayrollOut.model_validate(p) for p in payrolls],
        message="Nóminas listadas",
    )


@router.get("/pendientes")
async def list_pending(
    company_id: uuid.UUID, db: DbSession, _: RequireCompanyAccess
):
    payrolls = await payroll_service.list_pending_payrolls(db, company_id)
    return envelope(
        data=[PayrollPendingOut.model_validate(p) for p in payrolls],
        message="Nóminas pendientes de revisión",
    )


@router.get("/{payroll_id}")
async def get(
    company_id: uuid.UUID, payroll_id: uuid.UUID, db: DbSession, _: RequireCompanyAccess
):
    payroll = await payroll_service.get_payroll(db, company_id, payroll_id)
    return envelope(
        data=PayrollDetailedOut.model_validate(payroll),
        message="Nómina encontrada",
    )


@router.put("/{payroll_id}/detalle/{detail_id}")
async def edit_detail(
    company_id: uuid.UUID,
    payroll_id: uuid.UUID,
    detail_id: uuid.UUID,
    payload: PayrollDetailUpdate,
    db: DbSession,
    _: RequireCompanyAccess,
):
    payroll = await payroll_service.update_payroll_detail(
        db, company_id, payroll_id, detail_id, payload.model_dump(exclude_unset=True)
    )
    return envelope(
        data=PayrollDetailedOut.model_validate(payroll),
        message="Detalle de nómina actualizado",
    )


@router.post("/{payroll_id}/cerrar")
async def close(
    company_id: uuid.UUID, payroll_id: uuid.UUID, db: DbSession, _: RequireCompanyAccess
):
    payroll, warnings = await payroll_service.close_payroll(db, company_id, payroll_id)
    return envelope(
        data=PayrollDetailedOut.model_validate(payroll),
        message="Nómina cerrada",
        warnings=warnings,
    )


@router.get("/{payroll_id}/pdf")
async def payroll_pdf(
    company_id: uuid.UUID, payroll_id: uuid.UUID, db: DbSession, _: RequireCompanyAccess
):
    payroll, company, employees, incidents_by_employee = (
        await payroll_service.get_payroll_pdf_data(db, company_id, payroll_id)
    )
    pdf_bytes = pdf_service.generate_payroll_pdf(
        payroll, list(payroll.details), company, employees, incidents_by_employee
    )
    filename = f"nomina_{_slug_filename(company.name)}_{payroll.period_start}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{payroll_id}/empleados/{employee_id}/desprendible")
async def pay_stub_pdf(
    company_id: uuid.UUID,
    payroll_id: uuid.UUID,
    employee_id: uuid.UUID,
    db: DbSession,
    _: RequireCompanyAccess,
):
    detail, payroll, company, employee, contract = (
        await payroll_service.get_pay_stub_data(
            db, company_id, payroll_id, employee_id
        )
    )
    pdf_bytes = pdf_service.generate_pay_stub_pdf(
        detail, payroll, company, employee, contract
    )
    name = _slug_filename(f"{employee.first_name}_{employee.last_name}")
    filename = f"desprendible_{name}_{payroll.period_start}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
