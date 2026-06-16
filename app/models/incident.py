import enum
import uuid
from datetime import date as date_type, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class IncidentTypeEnum(str, enum.Enum):
    # Increase the payment
    DAY_OVERTIME = "day_overtime"            # 25% surcharge
    NIGHT_OVERTIME = "night_overtime"        # 75% surcharge
    HOLIDAY_OVERTIME = "holiday_overtime"    # 100% surcharge
    BONUS = "bonus"                          # Fixed amount
    COMMISSION = "commission"                # Fixed amount
    SPECIAL_ALLOWANCE = "special_allowance"  # Fixed amount
    PAID_VACATION = "paid_vacation"          # Days
    PAID_SICK_LEAVE = "paid_sick_leave"      # Days (company pays first 2)

    # Decrease the payment
    UNJUSTIFIED_ABSENCE = "unjustified_absence"  # Days/hours deducted
    LATE_ARRIVAL = "late_arrival"                # Hours deducted
    PAYROLL_DEDUCTION = "payroll_deduction"      # Fixed monthly amount
    GARNISHMENT = "garnishment"                  # Fixed amount
    PAYROLL_ADVANCE = "payroll_advance"          # Fixed amount
    OTHER_DEDUCTION = "other_deduction"          # Fixed amount


# Human-readable labels shown in responses (user-facing, kept in Spanish).
INCIDENT_TYPE_LABELS: dict["IncidentTypeEnum", str] = {
    IncidentTypeEnum.DAY_OVERTIME: "Hora extra diurna",
    IncidentTypeEnum.NIGHT_OVERTIME: "Hora extra nocturna",
    IncidentTypeEnum.HOLIDAY_OVERTIME: "Hora extra festivo",
    IncidentTypeEnum.BONUS: "Bonificación",
    IncidentTypeEnum.COMMISSION: "Comisión",
    IncidentTypeEnum.SPECIAL_ALLOWANCE: "Auxilio especial",
    IncidentTypeEnum.PAID_VACATION: "Vacaciones pagadas",
    IncidentTypeEnum.PAID_SICK_LEAVE: "Incapacidad pagada",
    IncidentTypeEnum.UNJUSTIFIED_ABSENCE: "Ausencia injustificada",
    IncidentTypeEnum.LATE_ARRIVAL: "Llegada tarde",
    IncidentTypeEnum.PAYROLL_DEDUCTION: "Descuento por libranza",
    IncidentTypeEnum.GARNISHMENT: "Descuento por embargo",
    IncidentTypeEnum.PAYROLL_ADVANCE: "Anticipo de nómina",
    IncidentTypeEnum.OTHER_DEDUCTION: "Otro descuento",
}


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )

    type: Mapped[IncidentTypeEnum] = mapped_column(
        SAEnum(IncidentTypeEnum, name="incident_type_enum"), nullable=False
    )
    date: Mapped[date_type] = mapped_column(Date, nullable=False)

    # Magnitude depending on the incident type.
    hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    days: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

    description: Mapped[str | None] = mapped_column(String(500))

    # Control
    applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    payroll_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("payrolls.id", ondelete="SET NULL"), index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    employee: Mapped["Employee"] = relationship(back_populates="incidents")  # noqa: F821
