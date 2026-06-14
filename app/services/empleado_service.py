import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.contrato import Contrato
from app.models.empleado import Empleado
from app.schemas.empleado import ContratoCreate, EmpleadoCreate, EmpleadoUpdate
from app.services.empresa_service import get_empresa


async def list_empleados(
    db: AsyncSession, empresa_id: uuid.UUID, incluir_inactivos: bool = False
) -> list[Empleado]:
    await get_empresa(db, empresa_id)
    stmt = (
        select(Empleado)
        .where(Empleado.empresa_id == empresa_id)
        .options(selectinload(Empleado.contrato))
        .order_by(Empleado.created_at.desc())
    )
    if not incluir_inactivos:
        stmt = stmt.where(Empleado.activo.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_empleado(
    db: AsyncSession, empresa_id: uuid.UUID, empleado_id: uuid.UUID
) -> Empleado:
    stmt = (
        select(Empleado)
        .where(Empleado.id == empleado_id, Empleado.empresa_id == empresa_id)
        .options(selectinload(Empleado.contrato))
    )
    result = await db.execute(stmt)
    empleado = result.scalar_one_or_none()
    if empleado is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado"
        )
    return empleado


async def _cedula_en_uso(
    db: AsyncSession,
    empresa_id: uuid.UUID,
    cedula: str,
    excluir_id: uuid.UUID | None = None,
) -> bool:
    stmt = select(Empleado).where(
        Empleado.empresa_id == empresa_id, Empleado.cedula == cedula
    )
    if excluir_id is not None:
        stmt = stmt.where(Empleado.id != excluir_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def create_empleado(
    db: AsyncSession, empresa_id: uuid.UUID, payload: EmpleadoCreate
) -> Empleado:
    await get_empresa(db, empresa_id)

    if await _cedula_en_uso(db, empresa_id, payload.cedula):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un empleado con la cédula {payload.cedula} en esta empresa",
        )

    empleado = Empleado(empresa_id=empresa_id, **payload.model_dump())
    db.add(empleado)
    await db.commit()
    return await get_empleado(db, empresa_id, empleado.id)


async def update_empleado(
    db: AsyncSession,
    empresa_id: uuid.UUID,
    empleado_id: uuid.UUID,
    payload: EmpleadoUpdate,
) -> Empleado:
    empleado = await get_empleado(db, empresa_id, empleado_id)
    data = payload.model_dump(exclude_unset=True)

    if "cedula" in data and data["cedula"] != empleado.cedula:
        if await _cedula_en_uso(db, empresa_id, data["cedula"], excluir_id=empleado_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un empleado con la cédula {data['cedula']} en esta empresa",
            )

    for field, value in data.items():
        setattr(empleado, field, value)

    await db.commit()
    return await get_empleado(db, empresa_id, empleado_id)


async def upsert_contrato(
    db: AsyncSession,
    empresa_id: uuid.UUID,
    empleado_id: uuid.UUID,
    payload: ContratoCreate,
) -> Contrato:
    empleado = await get_empleado(db, empresa_id, empleado_id)

    if (
        payload.tipo.value == "termino_fijo"
        and payload.fecha_fin is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Un contrato a término fijo requiere fecha_fin",
        )
    if payload.fecha_fin is not None and payload.fecha_fin < payload.fecha_inicio:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="fecha_fin no puede ser anterior a fecha_inicio",
        )

    contrato = empleado.contrato
    data = payload.model_dump()

    if contrato is None:
        contrato = Contrato(empleado_id=empleado_id, **data)
        db.add(contrato)
    else:
        for field, value in data.items():
            setattr(contrato, field, value)
        contrato.activo = True

    await db.commit()
    await db.refresh(contrato)
    return contrato
