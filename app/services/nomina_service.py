import uuid
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.contrato import Contrato
from app.models.empleado import Empleado
from app.models.nomina import EstadoNominaEnum, Nomina, NominaDetalle
from app.schemas.nomina import NominaGenerar
from app.services.empresa_service import get_empresa

# --------------------------------------------------------------------------- #
# Parámetros legales Colombia 2026
# --------------------------------------------------------------------------- #
SMMLV_2026 = Decimal("1750905")
AUXILIO_TRANSPORTE_2026 = Decimal("249095")
TOPE_AUXILIO_TRANSPORTE = SMMLV_2026 * 2  # 2 SMMLV

PORC_SALUD_EMPLEADO = Decimal("0.04")
PORC_PENSION_EMPLEADO = Decimal("0.04")

# Recargo de hora extra diurna (125%). Jornada base mensual = 240 horas.
HORAS_MES = Decimal("240")
RECARGO_HORA_EXTRA = Decimal("1.25")

_CENTAVOS = Decimal("0.01")


def _redondear(valor: Decimal) -> Decimal:
    return valor.quantize(_CENTAVOS, rounding=ROUND_HALF_UP)


def calcular_detalle(
    salario_base: Decimal,
    dias_trabajados: int = 30,
    horas_extra: Decimal = Decimal("0"),
) -> dict:
    """Aplica la lógica de cálculo de nómina para un empleado."""
    salario_base = Decimal(salario_base)

    # Auxilio de transporte: solo si el salario base <= 2 SMMLV
    auxilio_transporte = (
        AUXILIO_TRANSPORTE_2026
        if salario_base <= TOPE_AUXILIO_TRANSPORTE
        else Decimal("0")
    )

    valor_hora = salario_base / HORAS_MES
    valor_horas_extra = valor_hora * RECARGO_HORA_EXTRA * Decimal(horas_extra)

    salud_empleado = salario_base * PORC_SALUD_EMPLEADO
    pension_empleado = salario_base * PORC_PENSION_EMPLEADO
    total_deducciones = salud_empleado + pension_empleado

    total_devengado = salario_base + auxilio_transporte + valor_horas_extra
    neto_pagado = total_devengado - total_deducciones

    return {
        "salario_base": _redondear(salario_base),
        "dias_trabajados": dias_trabajados,
        "horas_extra": _redondear(Decimal(horas_extra)),
        "valor_horas_extra": _redondear(valor_horas_extra),
        "auxilio_transporte": _redondear(auxilio_transporte),
        "salud_empleado": _redondear(salud_empleado),
        "pension_empleado": _redondear(pension_empleado),
        "total_deducciones": _redondear(total_deducciones),
        "total_devengado": _redondear(total_devengado),
        "neto_pagado": _redondear(neto_pagado),
    }


async def generar_nomina(
    db: AsyncSession, empresa_id: uuid.UUID, payload: NominaGenerar
) -> Nomina:
    await get_empresa(db, empresa_id)

    # Empleados activos con contrato activo
    stmt = (
        select(Empleado)
        .join(Contrato, Contrato.empleado_id == Empleado.id)
        .where(
            Empleado.empresa_id == empresa_id,
            Empleado.activo.is_(True),
            Contrato.activo.is_(True),
        )
        .options(selectinload(Empleado.contrato))
    )
    result = await db.execute(stmt)
    empleados = list(result.scalars().all())

    if not empleados:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No hay empleados activos con contrato activo para generar la nómina",
        )

    nomina = Nomina(
        empresa_id=empresa_id,
        periodo_inicio=payload.periodo_inicio,
        periodo_fin=payload.periodo_fin,
        estado=EstadoNominaEnum.borrador,
    )

    total_devengado = Decimal("0.00")
    total_deducciones = Decimal("0.00")
    total_neto = Decimal("0.00")

    for empleado in empleados:
        calculo = calcular_detalle(empleado.contrato.salario_base)
        detalle = NominaDetalle(empleado_id=empleado.id, **calculo)
        nomina.detalles.append(detalle)

        total_devengado += detalle.total_devengado
        total_deducciones += detalle.total_deducciones
        total_neto += detalle.neto_pagado

    nomina.total_devengado = _redondear(total_devengado)
    nomina.total_deducciones = _redondear(total_deducciones)
    nomina.total_neto = _redondear(total_neto)

    db.add(nomina)
    await db.commit()
    return await get_nomina(db, empresa_id, nomina.id)


async def list_nominas(db: AsyncSession, empresa_id: uuid.UUID) -> list[Nomina]:
    await get_empresa(db, empresa_id)
    stmt = (
        select(Nomina)
        .where(Nomina.empresa_id == empresa_id)
        .order_by(Nomina.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_nomina(
    db: AsyncSession, empresa_id: uuid.UUID, nomina_id: uuid.UUID
) -> Nomina:
    stmt = (
        select(Nomina)
        .where(Nomina.id == nomina_id, Nomina.empresa_id == empresa_id)
        .options(selectinload(Nomina.detalles))
    )
    result = await db.execute(stmt)
    nomina = result.scalar_one_or_none()
    if nomina is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Nómina no encontrada"
        )

    # Cargar nombres de empleados y asignarlos a cada detalle
    ids = [d.empleado_id for d in nomina.detalles]
    if ids:
        res = await db.execute(select(Empleado).where(Empleado.id.in_(ids)))
        empleados = {e.id: e for e in res.scalars().all()}
        for d in nomina.detalles:
            emp = empleados.get(d.empleado_id)
            if emp:
                d.empleado_nombre = f"{emp.nombre} {emp.apellido}"

    return nomina

async def datos_pdf_nomina(
    db: AsyncSession, empresa_id: uuid.UUID, nomina_id: uuid.UUID
):
    """Reúne (nomina, empresa, {empleado_id: Empleado}) para el PDF de nómina."""
    from app.services.empresa_service import get_empresa as _get_empresa

    nomina = await get_nomina(db, empresa_id, nomina_id)
    empresa = await _get_empresa(db, empresa_id)

    ids = [d.empleado_id for d in nomina.detalles]
    empleados: dict[uuid.UUID, Empleado] = {}
    if ids:
        res = await db.execute(select(Empleado).where(Empleado.id.in_(ids)))
        empleados = {e.id: e for e in res.scalars().all()}

    return nomina, empresa, empleados


async def datos_desprendible(
    db: AsyncSession,
    empresa_id: uuid.UUID,
    nomina_id: uuid.UUID,
    empleado_id: uuid.UUID,
):
    """Reúne (detalle, nomina, empresa, empleado, contrato) para el desprendible."""
    from app.services.empleado_service import get_empleado as _get_empleado
    from app.services.empresa_service import get_empresa as _get_empresa

    nomina = await get_nomina(db, empresa_id, nomina_id)
    detalle = next(
        (d for d in nomina.detalles if d.empleado_id == empleado_id), None
    )
    if detalle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El empleado no tiene detalle en esta nómina",
        )

    empresa = await _get_empresa(db, empresa_id)
    empleado = await _get_empleado(db, empresa_id, empleado_id)
    contrato = empleado.contrato

    return detalle, nomina, empresa, empleado, contrato


async def cerrar_nomina(
    db: AsyncSession, empresa_id: uuid.UUID, nomina_id: uuid.UUID
) -> Nomina:
    nomina = await get_nomina(db, empresa_id, nomina_id)
    if nomina.estado == EstadoNominaEnum.cerrada:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La nómina ya se encuentra cerrada",
        )
    nomina.estado = EstadoNominaEnum.cerrada
    await db.commit()
    return await get_nomina(db, empresa_id, nomina_id)
