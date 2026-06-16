"""Automatic payroll generation logic by frequency.

The scheduler (``app/scheduler.py``) invokes ``generate_automatic_payrolls``
every day. This module holds the pure calendar logic (which company/employee
must be generated today) and the orchestration over the database.
"""

import logging
import uuid
from calendar import monthrange
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import PaymentFrequencyEnum
from app.models.company import Company
from app.models.payroll import Payroll
from app.schemas.payroll import PayrollGenerate
from app.services import payroll_service

logger = logging.getLogger("nomiapp.scheduler")


def _last_day_of_month(year: int, month: int) -> int:
    return monthrange(year, month)[1]


def should_generate_payroll(
    frequency: str, payment_day: int | None, today: date
) -> tuple[bool, date, date]:
    """Should a payroll be generated today for a company? + period (start, end).

    The returned period is the one used for the payroll when ``should`` is
    ``True``. When ``False`` the returned period is informational.
    """
    last = _last_day_of_month(today.year, today.month)

    if frequency == "monthly":
        # Effective payment day: payment_day (clamped to last day) or 30 default.
        target = payment_day if payment_day else 30
        target = min(target, last)
        start = today.replace(day=1)
        end = today.replace(day=target)
        return today.day == target, start, end

    if frequency == "biweekly":
        # Day 15 (1st half) and last day of the month (2nd half).
        if today.day == 15:
            return True, today.replace(day=1), today.replace(day=15)
        if today.day == last:
            return True, today.replace(day=16), today.replace(day=last)
        # Not due: informational period of the current half.
        if today.day < 15:
            return False, today.replace(day=1), today.replace(day=15)
        return False, today.replace(day=16), today.replace(day=last)

    if frequency == "weekly":
        # Every Friday; period Monday→Friday of that week.
        monday = today - timedelta(days=today.weekday())
        friday = monday + timedelta(days=4)
        return today.weekday() == 4, monday, friday

    return False, today, today


def employee_applies_today(
    employee_frequency: str, today: date
) -> tuple[bool, date, date]:
    """Should the employee (per their payment frequency) be included today?

    Does not depend on the company's ``payment_day``: for monthly it uses the
    last day of the month as the standard cut-off day.
    """
    return should_generate_payroll(employee_frequency, None, today)


async def generate_automatic_payrolls(db: AsyncSession, today: date) -> list[dict]:
    """Iterates active companies and generates the payrolls due today.

    Returns a list of results per company (generated, skipped, etc.).
    """
    result = await db.execute(select(Company).where(Company.active.is_(True)))
    companies = list(result.scalars().all())

    results: list[dict] = []

    for company in companies:
        frequency = company.payroll_frequency.value
        should, start, end = should_generate_payroll(
            frequency, company.payment_day, today
        )

        if not should:
            logger.info(
                "[scheduler] %s (%s): no payroll due today",
                company.name,
                frequency,
            )
            continue

        if await _payroll_exists(db, company.id, start, end):
            logger.info(
                "[scheduler] %s: payroll for period %s to %s already exists, skipping",
                company.name,
                start,
                end,
            )
            results.append(
                {
                    "company_id": str(company.id),
                    "company": company.name,
                    "period_start": start.isoformat(),
                    "period_end": end.isoformat(),
                    "status": "skipped_duplicate",
                }
            )
            continue

        try:
            payroll = await payroll_service.generate_payroll(
                db,
                company.id,
                PayrollGenerate(period_start=start, period_end=end),
                payment_frequency=PaymentFrequencyEnum(frequency),
            )
        except Exception as exc:  # no applicable employees or other validation
            logger.info(
                "[scheduler] %s: payroll not generated (%s)", company.name, exc
            )
            results.append(
                {
                    "company_id": str(company.id),
                    "company": company.name,
                    "period_start": start.isoformat(),
                    "period_end": end.isoformat(),
                    "status": "no_employees",
                }
            )
            continue

        logger.info(
            "[scheduler] %s: payroll %s generated for %s to %s (%d employees)",
            company.name,
            payroll.id,
            start,
            end,
            len(payroll.details),
        )
        results.append(
            {
                "company_id": str(company.id),
                "company": company.name,
                "payroll_id": str(payroll.id),
                "period_start": start.isoformat(),
                "period_end": end.isoformat(),
                "num_employees": len(payroll.details),
                "status": "generated",
            }
        )

    return results


async def _payroll_exists(
    db: AsyncSession, company_id: uuid.UUID, start: date, end: date
) -> bool:
    stmt = select(Payroll.id).where(
        Payroll.company_id == company_id,
        Payroll.period_start == start,
        Payroll.period_end == end,
    )
    result = await db.execute(stmt)
    return result.first() is not None
