import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class PayrollStatusEnum(str, enum.Enum):
    draft = "draft"
    closed = "closed"


class Payroll(Base):
    __tablename__ = "payrolls"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[PayrollStatusEnum] = mapped_column(
        SAEnum(PayrollStatusEnum, name="payroll_status_enum"),
        default=PayrollStatusEnum.draft,
        nullable=False,
    )
    total_earned: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    total_deductions: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    total_net: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    details: Mapped[list["PayrollDetail"]] = relationship(
        back_populates="payroll",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PayrollDetail(Base):
    __tablename__ = "payroll_details"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    payroll_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payrolls.id", ondelete="CASCADE"), index=True, nullable=False
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), index=True, nullable=False
    )
    base_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    days_worked: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    overtime_hours: Mapped[Decimal] = mapped_column(
        Numeric(8, 2), default=Decimal("0.00"), nullable=False
    )
    overtime_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    total_overtime_hours: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), default=Decimal("0.00"), nullable=False
    )
    total_bonuses: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    total_additional_deductions: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    transport_allowance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    health_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    pension_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_earned: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    net_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    manually_edited: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    payroll: Mapped["Payroll"] = relationship(back_populates="details")
