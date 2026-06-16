import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.incident import INCIDENT_TYPE_LABELS, IncidentTypeEnum


class IncidentCreate(BaseModel):
    type: IncidentTypeEnum
    date: date
    hours: Decimal | None = Field(None, ge=0, max_digits=6, decimal_places=2)
    days: Decimal | None = Field(None, ge=0, max_digits=6, decimal_places=2)
    amount: Decimal | None = Field(None, ge=0, max_digits=12, decimal_places=2)
    description: str | None = Field(None, max_length=500)

    @model_validator(mode="after")
    def validate_magnitude(self):
        if self.hours is None and self.days is None and self.amount is None:
            raise ValueError(
                "Debe especificar al menos uno de: horas, días o valor"
            )
        return self


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: uuid.UUID
    company_id: uuid.UUID
    type: IncidentTypeEnum
    type_label: str = ""
    date: date
    hours: Decimal | None = None
    days: Decimal | None = None
    amount: Decimal | None = None
    description: str | None = None
    applied: bool
    payroll_id: uuid.UUID | None = None
    created_at: datetime
    created_by: uuid.UUID | None = None

    @model_validator(mode="after")
    def set_type_label(self):
        self.type_label = INCIDENT_TYPE_LABELS.get(self.type, self.type.value)
        return self
