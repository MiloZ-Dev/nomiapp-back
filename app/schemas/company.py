import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

PayrollFrequency = Literal["weekly", "biweekly", "monthly"]


class CompanyBase(BaseModel):
    # Identification
    name: str = Field(..., min_length=1, max_length=255)
    nit: str = Field(..., min_length=1, max_length=50)
    legal_name: str | None = Field(None, max_length=200)
    trade_name: str | None = Field(None, max_length=200)
    document_type: str = Field("NIT", max_length=20)
    verification_digit: str | None = Field(None, max_length=1)

    # Contact and location
    city: str | None = None
    department: str | None = Field(None, max_length=100)
    country: str = Field("Colombia", max_length=100)
    postal_code: str | None = Field(None, max_length=10)
    address: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    website: str | None = Field(None, max_length=200)

    # Legal and tax information
    legal_representative: str | None = Field(None, max_length=200)
    economic_activity: str | None = Field(None, max_length=10)
    activity_description: str | None = Field(None, max_length=300)
    company_type: str | None = Field(None, max_length=50)
    tax_regime: str | None = Field(None, max_length=50)
    vat_responsible: bool = False

    # Payroll configuration
    payroll_frequency: PayrollFrequency = "monthly"
    payment_day: int | None = Field(None, ge=1, le=31)


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    """All fields optional. The ``nit`` cannot be modified."""

    name: str | None = Field(None, min_length=1, max_length=255)
    legal_name: str | None = Field(None, max_length=200)
    trade_name: str | None = Field(None, max_length=200)
    document_type: str | None = Field(None, max_length=20)
    verification_digit: str | None = Field(None, max_length=1)

    city: str | None = None
    department: str | None = Field(None, max_length=100)
    country: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=10)
    address: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    website: str | None = Field(None, max_length=200)

    legal_representative: str | None = Field(None, max_length=200)
    economic_activity: str | None = Field(None, max_length=10)
    activity_description: str | None = Field(None, max_length=300)
    company_type: str | None = Field(None, max_length=50)
    tax_regime: str | None = Field(None, max_length=50)
    vat_responsible: bool | None = None

    payroll_frequency: PayrollFrequency | None = None
    payment_day: int | None = Field(None, ge=1, le=31)

    active: bool | None = None


class CompanyOut(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    logo_url: str | None = None
    active: bool
    created_at: datetime


class CredentialsOut(BaseModel):
    email: str
    password: str


class CompanyCreatedResponse(BaseModel):
    company: CompanyOut
    credentials: CredentialsOut
