import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.payroll import PayrollStatusEnum


class PayrollGenerate(BaseModel):
    period_start: date
    period_end: date

    @model_validator(mode="after")
    def validate_period(self):
        if self.period_end < self.period_start:
            raise ValueError("period_end no puede ser anterior a period_start")
        return self


class PayrollDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    employee_name: str = ""
    base_salary: Decimal
    days_worked: int
    overtime_hours: Decimal
    overtime_value: Decimal
    total_overtime_hours: Decimal = Decimal("0")
    total_bonuses: Decimal = Decimal("0")
    total_additional_deductions: Decimal = Decimal("0")
    transport_allowance: Decimal
    health_deduction: Decimal
    pension_deduction: Decimal
    total_deductions: Decimal
    total_earned: Decimal
    net_pay: Decimal
    manually_edited: bool = False


class PayrollDetailUpdate(BaseModel):
    days_worked: int | None = Field(None, ge=0)
    overtime_hours: Decimal | None = Field(None, ge=0, max_digits=8, decimal_places=2)
    overtime_value: Decimal | None = Field(
        None, ge=0, max_digits=12, decimal_places=2
    )
    transport_allowance: Decimal | None = Field(
        None, ge=0, max_digits=12, decimal_places=2
    )
    total_bonuses: Decimal | None = Field(
        None, ge=0, max_digits=12, decimal_places=2
    )
    total_additional_deductions: Decimal | None = Field(
        None, ge=0, max_digits=12, decimal_places=2
    )


class PayrollOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    period_start: date
    period_end: date
    status: PayrollStatusEnum
    total_earned: Decimal
    total_deductions: Decimal
    total_net: Decimal
    created_at: datetime


class PayrollDetailedOut(PayrollOut):
    details: list[PayrollDetailOut] = []


class PayrollPendingOut(PayrollOut):
    """Draft payroll for the dashboard, with the employee count."""

    num_employees: int = 0


class AutomaticTriggerIn(BaseModel):
    # External JSON key stays "fecha" to preserve the request contract.
    model_config = ConfigDict(populate_by_name=True)

    run_date: date | None = Field(None, alias="fecha")
