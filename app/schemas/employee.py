import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.employee import PaymentFrequencyEnum
from app.models.contract import ContractTypeEnum
from app.schemas.incident import IncidentOut


# --------------------------------------------------------------------------- #
# Employee
# --------------------------------------------------------------------------- #
class EmployeeBase(BaseModel):
    # Identification
    first_name: str = Field(..., min_length=1, max_length=120)
    last_name: str = Field(..., min_length=1, max_length=120)
    id_number: str = Field(..., min_length=1, max_length=50)
    position: str = Field(..., min_length=1, max_length=120)
    document_type: str = Field("CC", max_length=20)
    document_number: str | None = Field(None, max_length=20)

    # Personal data
    middle_name: str | None = Field(None, max_length=100)
    second_last_name: str | None = Field(None, max_length=100)
    birth_date: date | None = None
    gender: str | None = Field(None, max_length=20)
    marital_status: str | None = Field(None, max_length=20)
    nationality: str = Field("Colombiana", max_length=100)

    # Contact
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    address: str | None = Field(None, max_length=300)
    city: str | None = Field(None, max_length=100)
    department: str | None = Field(None, max_length=100)

    # Banking information
    bank: str | None = Field(None, max_length=100)
    account_type: str | None = Field(None, max_length=20)
    account_number: str | None = Field(None, max_length=50)

    # Employment information
    employee_code: str | None = Field(None, max_length=20)
    area: str | None = Field(None, max_length=100)
    cost_center: str | None = Field(None, max_length=100)
    payment_frequency: PaymentFrequencyEnum = PaymentFrequencyEnum.monthly
    hire_date: date | None = None

    # Photo / document
    photo_url: str | None = Field(None, max_length=500)
    contract_url: str | None = Field(None, max_length=500)


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=120)
    last_name: str | None = Field(None, min_length=1, max_length=120)
    id_number: str | None = Field(None, min_length=1, max_length=50)
    position: str | None = Field(None, min_length=1, max_length=120)
    document_type: str | None = Field(None, max_length=20)
    document_number: str | None = Field(None, max_length=20)

    middle_name: str | None = Field(None, max_length=100)
    second_last_name: str | None = Field(None, max_length=100)
    birth_date: date | None = None
    gender: str | None = Field(None, max_length=20)
    marital_status: str | None = Field(None, max_length=20)
    nationality: str | None = Field(None, max_length=100)

    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=50)
    address: str | None = Field(None, max_length=300)
    city: str | None = Field(None, max_length=100)
    department: str | None = Field(None, max_length=100)

    bank: str | None = Field(None, max_length=100)
    account_type: str | None = Field(None, max_length=20)
    account_number: str | None = Field(None, max_length=50)

    employee_code: str | None = Field(None, max_length=20)
    area: str | None = Field(None, max_length=100)
    cost_center: str | None = Field(None, max_length=100)
    payment_frequency: PaymentFrequencyEnum | None = None
    hire_date: date | None = None

    photo_url: str | None = Field(None, max_length=500)
    contract_url: str | None = Field(None, max_length=500)

    active: bool | None = None


# --------------------------------------------------------------------------- #
# Contract
# --------------------------------------------------------------------------- #
class ContractBase(BaseModel):
    type: ContractTypeEnum
    base_salary: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    start_date: date
    end_date: date | None = None
    eps: str | None = None
    afp: str | None = None
    arl: str | None = None
    compensation_fund: str | None = None

    # Working conditions
    probation_period: bool = False
    probation_days: int | None = Field(None, ge=0)
    work_schedule: str = Field("Completa", max_length=50)
    weekly_hours: int = Field(48, ge=0)
    work_location: str | None = Field(None, max_length=200)
    modality: str = Field("Presencial", max_length=50)

    # Additional payments
    salary_in_kind: Decimal = Field(
        Decimal("0"), ge=0, max_digits=12, decimal_places=2
    )
    mobility_allowance: Decimal = Field(
        Decimal("0"), ge=0, max_digits=12, decimal_places=2
    )
    food_allowance: Decimal = Field(
        Decimal("0"), ge=0, max_digits=12, decimal_places=2
    )
    other_allowances: Decimal = Field(
        Decimal("0"), ge=0, max_digits=12, decimal_places=2
    )
    notes: str | None = None


class ContractCreate(ContractBase):
    pass


class ContractUpdate(BaseModel):
    type: ContractTypeEnum | None = None
    base_salary: Decimal | None = Field(None, gt=0, max_digits=12, decimal_places=2)
    start_date: date | None = None
    end_date: date | None = None
    eps: str | None = None
    afp: str | None = None
    arl: str | None = None
    compensation_fund: str | None = None

    probation_period: bool | None = None
    probation_days: int | None = Field(None, ge=0)
    work_schedule: str | None = Field(None, max_length=50)
    weekly_hours: int | None = Field(None, ge=0)
    work_location: str | None = Field(None, max_length=200)
    modality: str | None = Field(None, max_length=50)

    salary_in_kind: Decimal | None = Field(
        None, ge=0, max_digits=12, decimal_places=2
    )
    mobility_allowance: Decimal | None = Field(
        None, ge=0, max_digits=12, decimal_places=2
    )
    food_allowance: Decimal | None = Field(
        None, ge=0, max_digits=12, decimal_places=2
    )
    other_allowances: Decimal | None = Field(
        None, ge=0, max_digits=12, decimal_places=2
    )
    notes: str | None = None


class ContractOut(ContractBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    active: bool
    created_at: datetime


class EmployeeOut(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    active: bool
    created_at: datetime
    contract: ContractOut | None = None


class EmployeeDetailedOut(EmployeeOut):
    """Full employee + contract + pending incidents (applied=False)."""

    pending_incidents: list[IncidentOut] = []
