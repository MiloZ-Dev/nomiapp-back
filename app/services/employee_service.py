import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.contract import Contract
from app.models.employee import Employee
from app.models.incident import Incident
from app.schemas.employee import ContractCreate, EmployeeCreate, EmployeeUpdate
from app.services.company_service import get_company


async def list_employees(
    db: AsyncSession, company_id: uuid.UUID, include_inactive: bool = False
) -> list[Employee]:
    await get_company(db, company_id)
    stmt = (
        select(Employee)
        .where(Employee.company_id == company_id)
        .options(selectinload(Employee.contract))
        .order_by(Employee.created_at.desc())
    )
    if not include_inactive:
        stmt = stmt.where(Employee.active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_employee(
    db: AsyncSession, company_id: uuid.UUID, employee_id: uuid.UUID
) -> Employee:
    stmt = (
        select(Employee)
        .where(Employee.id == employee_id, Employee.company_id == company_id)
        .options(selectinload(Employee.contract))
    )
    result = await db.execute(stmt)
    employee = result.scalar_one_or_none()
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado"
        )
    return employee


async def _id_number_in_use(
    db: AsyncSession,
    company_id: uuid.UUID,
    id_number: str,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    stmt = select(Employee).where(
        Employee.company_id == company_id, Employee.id_number == id_number
    )
    if exclude_id is not None:
        stmt = stmt.where(Employee.id != exclude_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def create_employee(
    db: AsyncSession, company_id: uuid.UUID, payload: EmployeeCreate
) -> Employee:
    await get_company(db, company_id)

    if await _id_number_in_use(db, company_id, payload.id_number):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un empleado con la cédula {payload.id_number} en esta empresa",
        )

    employee = Employee(company_id=company_id, **payload.model_dump())
    db.add(employee)
    await db.commit()
    return await get_employee(db, company_id, employee.id)


async def update_employee(
    db: AsyncSession,
    company_id: uuid.UUID,
    employee_id: uuid.UUID,
    payload: EmployeeUpdate,
) -> Employee:
    employee = await get_employee(db, company_id, employee_id)
    data = payload.model_dump(exclude_unset=True)

    if "id_number" in data and data["id_number"] != employee.id_number:
        if await _id_number_in_use(
            db, company_id, data["id_number"], exclude_id=employee_id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un empleado con la cédula {data['id_number']} en esta empresa",
            )

    for field, value in data.items():
        setattr(employee, field, value)

    await db.commit()
    return await get_employee(db, company_id, employee_id)


async def get_employee_detailed(
    db: AsyncSession, company_id: uuid.UUID, employee_id: uuid.UUID
) -> Employee:
    """Employee with contract and pending incidents (applied=False)."""
    employee = await get_employee(db, company_id, employee_id)

    stmt = (
        select(Incident)
        .where(
            Incident.employee_id == employee_id,
            Incident.applied.is_(False),
        )
        .order_by(Incident.date.desc(), Incident.created_at.desc())
    )
    result = await db.execute(stmt)
    # Transient attribute consumed by EmployeeDetailedOut.
    employee.pending_incidents = list(result.scalars().all())
    return employee


async def set_photo_url(
    db: AsyncSession, company_id: uuid.UUID, employee_id: uuid.UUID, photo_url: str
) -> Employee:
    employee = await get_employee(db, company_id, employee_id)
    employee.photo_url = photo_url
    await db.commit()
    return await get_employee(db, company_id, employee_id)


async def set_contract_url(
    db: AsyncSession, company_id: uuid.UUID, employee_id: uuid.UUID, contract_url: str
) -> Employee:
    employee = await get_employee(db, company_id, employee_id)
    employee.contract_url = contract_url
    await db.commit()
    return await get_employee(db, company_id, employee_id)


async def upsert_contract(
    db: AsyncSession,
    company_id: uuid.UUID,
    employee_id: uuid.UUID,
    payload: ContractCreate,
) -> Contract:
    employee = await get_employee(db, company_id, employee_id)

    if payload.type.value == "fixed_term" and payload.end_date is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Un contrato a término fijo requiere fecha_fin",
        )
    if payload.end_date is not None and payload.end_date < payload.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="fecha_fin no puede ser anterior a fecha_inicio",
        )

    contract = employee.contract
    data = payload.model_dump()

    if contract is None:
        contract = Contract(employee_id=employee_id, **data)
        db.add(contract)
    else:
        for field, value in data.items():
            setattr(contract, field, value)
        contract.active = True

    await db.commit()
    await db.refresh(contract)
    return contract
