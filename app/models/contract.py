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
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class ContractTypeEnum(str, enum.Enum):
    fixed_term = "fixed_term"
    indefinite = "indefinite"
    work_contract = "work_contract"


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    type: Mapped[ContractTypeEnum] = mapped_column(
        SAEnum(ContractTypeEnum, name="contract_type_enum"), nullable=False
    )
    base_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    eps: Mapped[str | None] = mapped_column(String(120))
    afp: Mapped[str | None] = mapped_column(String(120))
    arl: Mapped[str | None] = mapped_column(String(120))
    compensation_fund: Mapped[str | None] = mapped_column(String(120))

    # Working conditions
    probation_period: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    probation_days: Mapped[int | None] = mapped_column(Integer)
    work_schedule: Mapped[str] = mapped_column(
        String(50), default="Completa", nullable=False
    )
    weekly_hours: Mapped[int] = mapped_column(Integer, default=48, nullable=False)
    work_location: Mapped[str | None] = mapped_column(String(200))
    modality: Mapped[str] = mapped_column(
        String(50), default="Presencial", nullable=False
    )

    # Additional payments
    salary_in_kind: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    mobility_allowance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    food_allowance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    other_allowances: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    employee: Mapped["Employee"] = relationship(back_populates="contract")  # noqa: F821
