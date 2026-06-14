import re
import secrets
import string
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.empresa import Empresa
from app.models.usuario import RolEnum, Usuario
from app.schemas.empresa import EmpresaCreate, EmpresaUpdate


def _slugify(nombre: str, max_len: int = 20) -> str:
    """'Carne SaS' -> 'carne-sas'. Solo alfanumérico + guión, máx max_len chars."""
    slug = nombre.lower().strip()
    slug = re.sub(r"\s+", "-", slug)          # espacios -> guión
    slug = re.sub(r"[^a-z0-9-]", "", slug)    # quitar lo no alfanumérico/guión
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    slug = slug[:max_len].strip("-")
    return slug or "empresa"


def _generar_password(length: int = 10) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


async def list_empresas(db: AsyncSession, incluir_inactivas: bool = False) -> list[Empresa]:
    stmt = select(Empresa).order_by(Empresa.created_at.desc())
    if not incluir_inactivas:
        stmt = stmt.where(Empresa.activo.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_empresa(db: AsyncSession, empresa_id: uuid.UUID) -> Empresa:
    empresa = await db.get(Empresa, empresa_id)
    if empresa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Empresa no encontrada"
        )
    return empresa


async def _generar_email_admin(db: AsyncSession, nombre: str) -> str:
    """admin@{slug}.nomiapp.co, garantizando unicidad si hay colisión."""
    slug = _slugify(nombre)
    base_email = f"admin@{slug}.nomiapp.co"

    existing = await db.execute(select(Usuario).where(Usuario.email == base_email))
    if existing.scalar_one_or_none() is None:
        return base_email

    # Colisión: agregar sufijo numérico hasta encontrar uno libre.
    for i in range(2, 1000):
        candidate = f"admin@{slug}-{i}.nomiapp.co"
        existing = await db.execute(select(Usuario).where(Usuario.email == candidate))
        if existing.scalar_one_or_none() is None:
            return candidate
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="No se pudo generar un email único para el admin de la empresa",
    )


async def create_empresa(db: AsyncSession, payload: EmpresaCreate) -> dict:
    """Crea la empresa y su usuario admin_empresa. Devuelve empresa + credenciales."""
    existing = await db.execute(select(Empresa).where(Empresa.nit == payload.nit))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una empresa con el NIT {payload.nit}",
        )

    empresa = Empresa(**payload.model_dump())
    db.add(empresa)
    await db.flush()  # asigna empresa.id sin cerrar la transacción

    email = await _generar_email_admin(db, empresa.nombre)
    password = _generar_password(10)

    admin = Usuario(
        email=email,
        hashed_password=hash_password(password),
        nombre=f"Admin {empresa.nombre}",
        rol=RolEnum.admin_empresa,
        empresa_id=empresa.id,
        activo=True,
    )
    db.add(admin)

    await db.commit()
    await db.refresh(empresa)

    return {
        "empresa": empresa,
        "credenciales": {"email": email, "password": password},
    }


async def update_empresa(
    db: AsyncSession, empresa_id: uuid.UUID, payload: EmpresaUpdate
) -> Empresa:
    empresa = await get_empresa(db, empresa_id)
    data = payload.model_dump(exclude_unset=True)

    if "nit" in data and data["nit"] != empresa.nit:
        existing = await db.execute(select(Empresa).where(Empresa.nit == data["nit"]))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una empresa con el NIT {data['nit']}",
            )

    for field, value in data.items():
        setattr(empresa, field, value)

    await db.commit()
    await db.refresh(empresa)
    return empresa


async def soft_delete_empresa(db: AsyncSession, empresa_id: uuid.UUID) -> Empresa:
    empresa = await get_empresa(db, empresa_id)
    empresa.activo = False
    await db.commit()
    await db.refresh(empresa)
    return empresa
