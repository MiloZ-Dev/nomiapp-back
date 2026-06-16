import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class PayrollFrequencyEnum(str, enum.Enum):
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    nit: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)

    # Legal identification
    legal_name: Mapped[str | None] = mapped_column(String(200))
    trade_name: Mapped[str | None] = mapped_column(String(200))
    document_type: Mapped[str] = mapped_column(String(20), default="NIT", nullable=False)
    verification_digit: Mapped[str | None] = mapped_column(String(1))

    # Contact and location
    city: Mapped[str | None] = mapped_column(String(120))
    department: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(100), default="Colombia", nullable=False)
    postal_code: Mapped[str | None] = mapped_column(String(10))
    address: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(200))
    website: Mapped[str | None] = mapped_column(String(200))

    # Legal and tax information
    legal_representative: Mapped[str | None] = mapped_column(String(200))
    economic_activity: Mapped[str | None] = mapped_column(String(10))
    activity_description: Mapped[str | None] = mapped_column(String(300))
    company_type: Mapped[str | None] = mapped_column(String(50))
    tax_regime: Mapped[str | None] = mapped_column(String(50))
    vat_responsible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Payroll configuration
    payroll_frequency: Mapped[PayrollFrequencyEnum] = mapped_column(
        SAEnum(PayrollFrequencyEnum, name="payroll_frequency_enum"),
        default=PayrollFrequencyEnum.monthly,
        nullable=False,
    )
    payment_day: Mapped[int | None] = mapped_column(Integer)

    # Branding
    logo_url: Mapped[str | None] = mapped_column(String(500))

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    employees: Mapped[list["Employee"]] = relationship(  # noqa: F821
        back_populates="company", cascade="all, delete-orphan"
    )
