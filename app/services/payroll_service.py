import uuid
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.contract import Contract
from app.models.employee import Employee, PaymentFrequencyEnum
from app.models.incident import Incident, IncidentTypeEnum
from app.models.payroll import Payroll, PayrollDetail, PayrollStatusEnum
from app.schemas.payroll import PayrollGenerate
from app.services.company_service import get_company

# --------------------------------------------------------------------------- #
# Colombia 2026 legal parameters
# --------------------------------------------------------------------------- #
SMMLV_2026 = Decimal("1750905")
TRANSPORT_ALLOWANCE_2026 = Decimal("249095")
TRANSPORT_ALLOWANCE_CAP = SMMLV_2026 * 2  # 2 SMMLV

HEALTH_EMPLOYEE_RATE = Decimal("0.04")
PENSION_EMPLOYEE_RATE = Decimal("0.04")

# Day overtime surcharge (125%). Base monthly working hours = 240.
HOURS_PER_MONTH = Decimal("240")
DAYS_PER_MONTH = Decimal("30")
OVERTIME_SURCHARGE = Decimal("1.25")

# Surcharge by overtime type (multiplier over the hourly rate).
SURCHARGE_BY_TYPE = {
    IncidentTypeEnum.DAY_OVERTIME: Decimal("1.25"),
    IncidentTypeEnum.NIGHT_OVERTIME: Decimal("1.75"),
    IncidentTypeEnum.HOLIDAY_OVERTIME: Decimal("2.0"),
}

# Fixed-amount incidents added directly to earnings.
FIXED_EARNING_TYPES = {
    IncidentTypeEnum.BONUS,
    IncidentTypeEnum.COMMISSION,
    IncidentTypeEnum.SPECIAL_ALLOWANCE,
    IncidentTypeEnum.PAID_SICK_LEAVE,
}

# Fixed-amount incidents added directly to deductions.
FIXED_DEDUCTION_TYPES = {
    IncidentTypeEnum.PAYROLL_DEDUCTION,
    IncidentTypeEnum.GARNISHMENT,
    IncidentTypeEnum.PAYROLL_ADVANCE,
    IncidentTypeEnum.OTHER_DEDUCTION,
}

_CENTS = Decimal("0.01")


def _round(value: Decimal) -> Decimal:
    return value.quantize(_CENTS, rounding=ROUND_HALF_UP)


def calculate_payroll_detail(
    base_salary: Decimal,
    days_worked: int = 30,
    overtime_hours: Decimal = Decimal("0"),
    incidents: list[Incident] | None = None,
) -> dict:
    """Applies the payroll calculation logic for a single employee.

    ``incidents`` is the list of incidents for the period (applied=False). Each
    one adjusts earnings or deductions depending on its type.
    """
    base_salary = Decimal(base_salary)
    incidents = incidents or []

    # Transport allowance: only if base salary <= 2 SMMLV.
    transport_allowance = (
        TRANSPORT_ALLOWANCE_2026
        if base_salary <= TRANSPORT_ALLOWANCE_CAP
        else Decimal("0")
    )

    hourly_rate = base_salary / HOURS_PER_MONTH
    daily_rate = base_salary / DAYS_PER_MONTH

    # Legacy overtime (loose parameter) with the default day surcharge.
    total_overtime_hours = Decimal(overtime_hours)
    overtime_value = hourly_rate * OVERTIME_SURCHARGE * Decimal(overtime_hours)

    total_bonuses = Decimal("0")
    total_additional_deductions = Decimal("0")
    extra_earned = Decimal("0")  # bonuses + overtime + other earnings
    extra_deductions = Decimal("0")
    applied_incidents: list = []

    for inc in incidents:
        inc_type = inc.type
        hours = Decimal(inc.hours) if inc.hours is not None else Decimal("0")
        days = Decimal(inc.days) if inc.days is not None else Decimal("0")
        amount = Decimal(inc.amount) if inc.amount is not None else Decimal("0")

        if inc_type in SURCHARGE_BY_TYPE:
            surcharge = hourly_rate * SURCHARGE_BY_TYPE[inc_type] * hours
            overtime_value += surcharge
            total_overtime_hours += hours
            extra_earned += surcharge
        elif inc_type in FIXED_EARNING_TYPES:
            extra_earned += amount
            total_bonuses += amount
        elif inc_type == IncidentTypeEnum.PAID_VACATION:
            value = daily_rate * days
            extra_earned += value
            total_bonuses += value
        elif inc_type == IncidentTypeEnum.UNJUSTIFIED_ABSENCE:
            value = daily_rate * days
            extra_earned -= value
            total_additional_deductions += value
        elif inc_type == IncidentTypeEnum.LATE_ARRIVAL:
            value = hourly_rate * hours
            extra_earned -= value
            total_additional_deductions += value
        elif inc_type in FIXED_DEDUCTION_TYPES:
            extra_deductions += amount
            total_additional_deductions += amount
        else:
            continue

        applied_incidents.append(inc.id)

    health_deduction = base_salary * HEALTH_EMPLOYEE_RATE
    pension_deduction = base_salary * PENSION_EMPLOYEE_RATE
    total_deductions = health_deduction + pension_deduction + extra_deductions

    total_earned = base_salary + transport_allowance + extra_earned
    net_pay = total_earned - total_deductions

    return {
        "base_salary": _round(base_salary),
        "days_worked": days_worked,
        "overtime_hours": _round(total_overtime_hours),
        "overtime_value": _round(overtime_value),
        "total_overtime_hours": _round(total_overtime_hours),
        "total_bonuses": _round(total_bonuses),
        "total_additional_deductions": _round(total_additional_deductions),
        "transport_allowance": _round(transport_allowance),
        "health_deduction": _round(health_deduction),
        "pension_deduction": _round(pension_deduction),
        "total_deductions": _round(total_deductions),
        "total_earned": _round(total_earned),
        "net_pay": _round(net_pay),
        "_applied_incidents": applied_incidents,
    }


async def generate_payroll(
    db: AsyncSession,
    company_id: uuid.UUID,
    payload: PayrollGenerate,
    payment_frequency: PaymentFrequencyEnum | None = None,
) -> Payroll:
    await get_company(db, company_id)

    # Active employees with an active contract.
    stmt = (
        select(Employee)
        .join(Contract, Contract.employee_id == Employee.id)
        .where(
            Employee.company_id == company_id,
            Employee.active.is_(True),
            Contract.active.is_(True),
        )
        .options(selectinload(Employee.contract))
    )
    # Optional filter by payment frequency (used by the scheduler).
    if payment_frequency is not None:
        stmt = stmt.where(Employee.payment_frequency == payment_frequency)
    result = await db.execute(stmt)
    employees = list(result.scalars().all())

    if not employees:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No hay empleados activos con contrato activo para generar la nómina",
        )

    # Pending incidents (applied=False) whose date falls inside the period,
    # grouped by employee.
    inc_stmt = select(Incident).where(
        Incident.company_id == company_id,
        Incident.applied.is_(False),
        Incident.date >= payload.period_start,
        Incident.date <= payload.period_end,
    )
    inc_result = await db.execute(inc_stmt)
    all_incidents = list(inc_result.scalars().all())
    incidents_by_employee: dict[uuid.UUID, list[Incident]] = {}
    for inc in all_incidents:
        incidents_by_employee.setdefault(inc.employee_id, []).append(inc)

    payroll = Payroll(
        company_id=company_id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        status=PayrollStatusEnum.draft,
    )

    total_earned = Decimal("0.00")
    total_deductions = Decimal("0.00")
    total_net = Decimal("0.00")
    applied_ids: list[uuid.UUID] = []

    for employee in employees:
        calc = calculate_payroll_detail(
            employee.contract.base_salary,
            incidents=incidents_by_employee.get(employee.id, []),
        )
        applied_ids.extend(calc.pop("_applied_incidents"))
        detail = PayrollDetail(employee_id=employee.id, **calc)
        payroll.details.append(detail)

        total_earned += detail.total_earned
        total_deductions += detail.total_deductions
        total_net += detail.net_pay

    payroll.total_earned = _round(total_earned)
    payroll.total_deductions = _round(total_deductions)
    payroll.total_net = _round(total_net)

    db.add(payroll)
    await db.flush()  # assigns payroll.id before marking the incidents

    # Mark the processed incidents as applied and link them to the payroll.
    applied_ids_set = set(applied_ids)
    for inc in all_incidents:
        if inc.id in applied_ids_set:
            inc.applied = True
            inc.payroll_id = payroll.id

    await db.commit()
    return await get_payroll(db, company_id, payroll.id)


async def list_payrolls(db: AsyncSession, company_id: uuid.UUID) -> list[Payroll]:
    await get_company(db, company_id)
    stmt = (
        select(Payroll)
        .where(Payroll.company_id == company_id)
        .order_by(Payroll.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_payroll(
    db: AsyncSession, company_id: uuid.UUID, payroll_id: uuid.UUID
) -> Payroll:
    stmt = (
        select(Payroll)
        .where(Payroll.id == payroll_id, Payroll.company_id == company_id)
        .options(selectinload(Payroll.details))
    )
    result = await db.execute(stmt)
    payroll = result.scalar_one_or_none()
    if payroll is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Nómina no encontrada"
        )

    # Load employee names and attach them to each detail.
    ids = [d.employee_id for d in payroll.details]
    if ids:
        res = await db.execute(select(Employee).where(Employee.id.in_(ids)))
        employees = {e.id: e for e in res.scalars().all()}
        for d in payroll.details:
            emp = employees.get(d.employee_id)
            if emp:
                d.employee_name = f"{emp.first_name} {emp.last_name}"

    return payroll


async def get_payroll_pdf_data(
    db: AsyncSession, company_id: uuid.UUID, payroll_id: uuid.UUID
):
    """Gathers (payroll, company, {employee_id: Employee}) for the payroll PDF."""
    payroll = await get_payroll(db, company_id, payroll_id)
    company = await get_company(db, company_id)

    ids = [d.employee_id for d in payroll.details]
    employees: dict[uuid.UUID, Employee] = {}
    if ids:
        res = await db.execute(select(Employee).where(Employee.id.in_(ids)))
        employees = {e.id: e for e in res.scalars().all()}

    return payroll, company, employees


async def get_pay_stub_data(
    db: AsyncSession,
    company_id: uuid.UUID,
    payroll_id: uuid.UUID,
    employee_id: uuid.UUID,
):
    """Gathers (detail, payroll, company, employee, contract) for the pay stub."""
    from app.services.employee_service import get_employee

    payroll = await get_payroll(db, company_id, payroll_id)
    detail = next(
        (d for d in payroll.details if d.employee_id == employee_id), None
    )
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El empleado no tiene detalle en esta nómina",
        )

    company = await get_company(db, company_id)
    employee = await get_employee(db, company_id, employee_id)
    contract = employee.contract

    return detail, payroll, company, employee, contract


async def close_payroll(
    db: AsyncSession, company_id: uuid.UUID, payroll_id: uuid.UUID
) -> tuple[Payroll, list[str]]:
    payroll = await get_payroll(db, company_id, payroll_id)
    if payroll.status == PayrollStatusEnum.closed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La nómina ya se encuentra cerrada",
        )

    # The payroll must have at least one detail to be closed.
    if not payroll.details:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No se puede cerrar una nómina sin empleados",
        )

    # A negative net does not block closing, but is reported as a warning.
    warnings: list[str] = []
    for d in payroll.details:
        if d.net_pay < 0:
            name = getattr(d, "employee_name", "") or str(d.employee_id)
            warnings.append(
                f"Empleado {name} tiene neto negativo: $ {d.net_pay:,.2f}"
            )

    payroll.status = PayrollStatusEnum.closed
    await db.commit()

    payroll = await get_payroll(db, company_id, payroll_id)
    await _send_pay_stubs(db, company_id, payroll)
    return payroll, warnings


async def _send_pay_stubs(
    db: AsyncSession, company_id: uuid.UUID, payroll: Payroll
) -> None:
    """Emails the pay stub to each employee with an email (best-effort).

    An email failure never interrupts closing the payroll.
    """
    from app.services.email_service import send_pay_stub
    from app.services.pdf_service import generate_pay_stub_pdf

    company = await get_company(db, company_id)

    ids = [d.employee_id for d in payroll.details]
    if not ids:
        return
    res = await db.execute(
        select(Employee)
        .where(Employee.id.in_(ids))
        .options(selectinload(Employee.contract))
    )
    employees_dict = {e.id: e for e in res.scalars().all()}

    for detail in payroll.details:
        employee = employees_dict.get(detail.employee_id)
        if employee is None or not employee.email:
            continue
        contract = employee.contract
        if not contract:
            continue

        try:
            pdf_bytes = generate_pay_stub_pdf(
                detail, payroll, company, employee, contract
            )
            formatted_net = f"$ {int(detail.net_pay):,}".replace(",", ".")
            await send_pay_stub(
                employee_email=employee.email,
                employee_name=f"{employee.first_name} {employee.last_name}",
                company_name=company.name,
                period_start=str(payroll.period_start),
                period_end=str(payroll.period_end),
                pdf_bytes=pdf_bytes,
                net_pay=formatted_net,
            )
        except Exception as e:
            print(f"[payroll] Error sending pay stub to {employee.email}: {e}")
            continue  # Do not block on an email failure.


async def list_pending_payrolls(
    db: AsyncSession, company_id: uuid.UUID
) -> list[Payroll]:
    """Draft payrolls, with ``num_employees`` (detail count)."""
    await get_company(db, company_id)
    stmt = (
        select(Payroll)
        .where(
            Payroll.company_id == company_id,
            Payroll.status == PayrollStatusEnum.draft,
        )
        .options(selectinload(Payroll.details))
        .order_by(Payroll.created_at.desc())
    )
    result = await db.execute(stmt)
    payrolls = list(result.scalars().all())
    for p in payrolls:
        p.num_employees = len(p.details)
    return payrolls


async def recalculate_payroll_totals(db: AsyncSession, payroll: Payroll) -> None:
    """Recalculates and persists the payroll totals from its details."""
    payroll.total_earned = _round(
        sum((d.total_earned for d in payroll.details), Decimal("0"))
    )
    payroll.total_deductions = _round(
        sum((d.total_deductions for d in payroll.details), Decimal("0"))
    )
    payroll.total_net = _round(
        sum((d.net_pay for d in payroll.details), Decimal("0"))
    )
    await db.commit()


async def update_payroll_detail(
    db: AsyncSession,
    company_id: uuid.UUID,
    payroll_id: uuid.UUID,
    detail_id: uuid.UUID,
    changes: dict,
) -> Payroll:
    """Edits a detail of a draft payroll and recalculates totals.

    ``changes`` are the provided (exclude_unset) fields of PayrollDetailUpdate.
    """
    payroll = await get_payroll(db, company_id, payroll_id)
    if payroll.status != PayrollStatusEnum.draft:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Solo se pueden editar nóminas en estado borrador",
        )

    detail = next((d for d in payroll.details if d.id == detail_id), None)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Detalle de nómina no encontrado",
        )

    for field, value in changes.items():
        setattr(detail, field, value)

    # Recalculate the detail with the current variable fields.
    detail.total_earned = _round(
        detail.base_salary
        + detail.transport_allowance
        + detail.overtime_value
        + detail.total_bonuses
    )
    detail.total_deductions = _round(
        detail.health_deduction
        + detail.pension_deduction
        + detail.total_additional_deductions
    )
    detail.net_pay = _round(detail.total_earned - detail.total_deductions)
    detail.manually_edited = True

    await recalculate_payroll_totals(db, payroll)
    return await get_payroll(db, company_id, payroll_id)
