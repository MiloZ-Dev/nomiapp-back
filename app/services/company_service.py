import re
import secrets
import string
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.company import Company, PayrollFrequencyEnum
from app.models.user import RoleEnum, User
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.services.email_service import send_welcome_email


def _slugify(name: str, max_len: int = 20) -> str:
    """'Carne SaS' -> 'carne-sas'. Only alphanumeric + dash, max max_len chars."""
    slug = name.lower().strip()
    slug = re.sub(r"\s+", "-", slug)          # spaces -> dash
    slug = re.sub(r"[^a-z0-9-]", "", slug)    # drop non alphanumeric/dash
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    slug = slug[:max_len].strip("-")
    return slug or "company"


def _generate_password(length: int = 10) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


async def list_companies(
    db: AsyncSession, include_inactive: bool = False
) -> list[Company]:
    stmt = select(Company).order_by(Company.created_at.desc())
    if not include_inactive:
        stmt = stmt.where(Company.active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_company(db: AsyncSession, company_id: uuid.UUID) -> Company:
    company = await db.get(Company, company_id)
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Empresa no encontrada"
        )
    return company


async def _generate_admin_email(db: AsyncSession, name: str) -> str:
    """admin@{slug}.nomiapp.co, guaranteeing uniqueness on collision."""
    slug = _slugify(name)
    base_email = f"admin@{slug}.nomiapp.co"

    existing = await db.execute(select(User).where(User.email == base_email))
    if existing.scalar_one_or_none() is None:
        return base_email

    # Collision: append a numeric suffix until a free one is found.
    for i in range(2, 1000):
        candidate = f"admin@{slug}-{i}.nomiapp.co"
        existing = await db.execute(select(User).where(User.email == candidate))
        if existing.scalar_one_or_none() is None:
            return candidate
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="No se pudo generar un email único para el admin de la empresa",
    )


async def create_company(db: AsyncSession, payload: CompanyCreate) -> dict:
    """Create the company and its company_admin user. Returns company + credentials."""
    existing = await db.execute(select(Company).where(Company.nit == payload.nit))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una empresa con el NIT {payload.nit}",
        )

    data = payload.model_dump()
    if data.get("payroll_frequency") is not None:
        data["payroll_frequency"] = PayrollFrequencyEnum(data["payroll_frequency"])

    company = Company(**data)
    db.add(company)
    await db.flush()  # assigns company.id without closing the transaction

    email = await _generate_admin_email(db, company.name)
    password = _generate_password(10)

    admin = User(
        email=email,
        hashed_password=hash_password(password),
        name=f"Admin {company.name}",
        role=RoleEnum.company_admin,
        company_id=company.id,
        active=True,
    )
    db.add(admin)

    await db.commit()
    await db.refresh(company)

    # Welcome email with credentials (does not block if it fails / no API key).
    await send_welcome_email(
        admin_email=email,
        company_name=company.name,
        temporary_password=password,
    )

    return {
        "company": company,
        "credentials": {"email": email, "password": password},
    }


async def update_company(
    db: AsyncSession, company_id: uuid.UUID, payload: CompanyUpdate
) -> Company:
    company = await get_company(db, company_id)
    data = payload.model_dump(exclude_unset=True)

    # The NIT is immutable: ignored even if it comes in the payload.
    data.pop("nit", None)

    if data.get("payroll_frequency") is not None:
        data["payroll_frequency"] = PayrollFrequencyEnum(data["payroll_frequency"])

    for field, value in data.items():
        setattr(company, field, value)

    await db.commit()
    await db.refresh(company)
    return company


async def set_logo_url(
    db: AsyncSession, company_id: uuid.UUID, logo_url: str
) -> Company:
    company = await get_company(db, company_id)
    company.logo_url = logo_url
    await db.commit()
    await db.refresh(company)
    return company


async def soft_delete_company(db: AsyncSession, company_id: uuid.UUID) -> Company:
    company = await get_company(db, company_id)
    company.active = False
    await db.commit()
    await db.refresh(company)
    return company
