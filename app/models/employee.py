import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class PaymentFrequencyEnum(str, enum.Enum):
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint("company_id", "id_number", name="uq_employee_company_id_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Identification
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    id_number: Mapped[str] = mapped_column(String(50), nullable=False)
    document_type: Mapped[str] = mapped_column(String(20), default="CC", nullable=False)
    document_number: Mapped[str | None] = mapped_column(String(20))

    # Personal data
    middle_name: Mapped[str | None] = mapped_column(String(100))
    second_last_name: Mapped[str | None] = mapped_column(String(100))
    birth_date: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(20))
    marital_status: Mapped[str | None] = mapped_column(String(20))
    nationality: Mapped[str] = mapped_column(
        String(100), default="Colombiana", nullable=False
    )

    # Contact
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(String(300))
    city: Mapped[str | None] = mapped_column(String(100))
    department: Mapped[str | None] = mapped_column(String(100))

    # Banking information (for payment)
    bank: Mapped[str | None] = mapped_column(String(100))
    account_type: Mapped[str | None] = mapped_column(String(20))
    account_number: Mapped[str | None] = mapped_column(String(50))

    # Employment information
    position: Mapped[str | None] = mapped_column(String(120))
    employee_code: Mapped[str | None] = mapped_column(String(20))
    area: Mapped[str | None] = mapped_column(String(100))
    cost_center: Mapped[str | None] = mapped_column(String(100))
    payment_frequency: Mapped[PaymentFrequencyEnum] = mapped_column(
        SAEnum(PaymentFrequencyEnum, name="payment_frequency_enum"),
        default=PaymentFrequencyEnum.monthly,
        nullable=False,
    )
    hire_date: Mapped[date | None] = mapped_column(Date)

    # Photo / document
    photo_url: Mapped[str | None] = mapped_column(String(500))
    contract_url: Mapped[str | None] = mapped_column(String(500))

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    company: Mapped["Company"] = relationship(back_populates="employees")  # noqa: F821
    contract: Mapped["Contract | None"] = relationship(  # noqa: F821
        back_populates="employee",
        uselist=False,
        cascade="all, delete-orphan",
    )
    incidents: Mapped[list["Incident"]] = relationship(  # noqa: F821
        back_populates="employee",
        cascade="all, delete-orphan",
    )
