import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident
from app.schemas.incident import IncidentCreate
from app.services.employee_service import get_employee


async def create_incident(
    db: AsyncSession,
    company_id: uuid.UUID,
    employee_id: uuid.UUID,
    payload: IncidentCreate,
    created_by: uuid.UUID | None = None,
) -> Incident:
    # Validate that the employee exists and belongs to the company.
    await get_employee(db, company_id, employee_id)

    incident = Incident(
        employee_id=employee_id,
        company_id=company_id,
        created_by=created_by,
        **payload.model_dump(),
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    return incident


async def list_incidents(
    db: AsyncSession,
    company_id: uuid.UUID,
    employee_id: uuid.UUID,
    applied: bool | None = False,
    month: str | None = None,
) -> list[Incident]:
    await get_employee(db, company_id, employee_id)

    stmt = select(Incident).where(
        Incident.company_id == company_id,
        Incident.employee_id == employee_id,
    )
    if applied is not None:
        stmt = stmt.where(Incident.applied.is_(applied))
    if month is not None:
        start, end = _month_range(month)
        stmt = stmt.where(Incident.date >= start, Incident.date <= end)

    stmt = stmt.order_by(Incident.date.desc(), Incident.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def delete_incident(
    db: AsyncSession,
    company_id: uuid.UUID,
    employee_id: uuid.UUID,
    incident_id: uuid.UUID,
) -> None:
    await get_employee(db, company_id, employee_id)

    stmt = select(Incident).where(
        Incident.id == incident_id,
        Incident.company_id == company_id,
        Incident.employee_id == employee_id,
    )
    result = await db.execute(stmt)
    incident = result.scalar_one_or_none()
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Novedad no encontrada"
        )
    if incident.applied:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar una novedad ya aplicada en una nómina",
        )

    await db.delete(incident)
    await db.commit()


def _month_range(month: str) -> tuple[str, str]:
    """Converts ``YYYY-MM`` into (first day, last day) as ISO strings."""
    from calendar import monthrange
    from datetime import date

    try:
        year, m = (int(p) for p in month.split("-"))
        start = date(year, m, 1)
        end = date(year, m, monthrange(year, m)[1])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El parámetro 'mes' debe tener formato YYYY-MM",
        )
    return start.isoformat(), end.isoformat()
