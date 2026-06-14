import re
import uuid
from io import BytesIO

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse

from app.api.responses import envelope
from app.core.dependencies import DbSession, RequireEmpresaAccess
from app.schemas.nomina import NominaDetalladaOut, NominaGenerar, NominaOut
from app.services import nomina_service, pdf_service

router = APIRouter(prefix="/empresas/{empresa_id}/nomina", tags=["nomina"])


def _slug_archivo(texto: str) -> str:
    """Normaliza un texto para usarlo en un nombre de archivo."""
    s = re.sub(r"[^A-Za-z0-9]+", "_", texto).strip("_")
    return s or "archivo"


@router.post("/generar", status_code=status.HTTP_201_CREATED)
async def generar(
    empresa_id: uuid.UUID, payload: NominaGenerar, db: DbSession, _: RequireEmpresaAccess
):
    nomina = await nomina_service.generar_nomina(db, empresa_id, payload)
    return envelope(
        data=NominaDetalladaOut.model_validate(nomina),
        message="Nómina generada en estado borrador",
    )


@router.get("/")
async def listar(empresa_id: uuid.UUID, db: DbSession, _: RequireEmpresaAccess):
    nominas = await nomina_service.list_nominas(db, empresa_id)
    return envelope(
        data=[NominaOut.model_validate(n) for n in nominas],
        message="Nóminas listadas",
    )


@router.get("/{nomina_id}")
async def obtener(
    empresa_id: uuid.UUID, nomina_id: uuid.UUID, db: DbSession, _: RequireEmpresaAccess
):
    nomina = await nomina_service.get_nomina(db, empresa_id, nomina_id)
    return envelope(
        data=NominaDetalladaOut.model_validate(nomina),
        message="Nómina encontrada",
    )


@router.post("/{nomina_id}/cerrar")
async def cerrar(
    empresa_id: uuid.UUID, nomina_id: uuid.UUID, db: DbSession, _: RequireEmpresaAccess
):
    nomina = await nomina_service.cerrar_nomina(db, empresa_id, nomina_id)
    return envelope(
        data=NominaDetalladaOut.model_validate(nomina),
        message="Nómina cerrada",
    )


@router.get("/{nomina_id}/pdf")
async def pdf_nomina(
    empresa_id: uuid.UUID, nomina_id: uuid.UUID, db: DbSession, _: RequireEmpresaAccess
):
    nomina, empresa, empleados = await nomina_service.datos_pdf_nomina(
        db, empresa_id, nomina_id
    )
    pdf_bytes = pdf_service.generar_pdf_nomina(
        nomina, list(nomina.detalles), empresa, empleados
    )
    filename = f"nomina_{_slug_archivo(empresa.nombre)}_{nomina.periodo_inicio}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{nomina_id}/empleados/{empleado_id}/desprendible")
async def pdf_desprendible(
    empresa_id: uuid.UUID,
    nomina_id: uuid.UUID,
    empleado_id: uuid.UUID,
    db: DbSession,
    _: RequireEmpresaAccess,
):
    detalle, nomina, empresa, empleado, contrato = (
        await nomina_service.datos_desprendible(
            db, empresa_id, nomina_id, empleado_id
        )
    )
    pdf_bytes = pdf_service.generar_pdf_desprendible(
        detalle, nomina, empresa, empleado, contrato
    )
    nombre = _slug_archivo(f"{empleado.nombre}_{empleado.apellido}")
    filename = f"desprendible_{nombre}_{nomina.periodo_inicio}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
