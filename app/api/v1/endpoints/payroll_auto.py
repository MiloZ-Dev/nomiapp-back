"""Global automatic payroll generation endpoint (manual trigger).

Lives outside the ``/empresas/{company_id}`` prefix because it evaluates all
companies. Restricted to super_admin; useful for demos and tests without
waiting for the daily 6 AM job.
"""

from datetime import date

from fastapi import APIRouter

from app.api.responses import envelope
from app.core.dependencies import DbSession, RequireSuperAdmin
from app.schemas.payroll import AutomaticTriggerIn
from app.services import scheduler_service

router = APIRouter(prefix="/nomina", tags=["payroll-automatic"])


@router.post("/trigger-automatico")
async def trigger_automatic(
    payload: AutomaticTriggerIn,
    db: DbSession,
    _: RequireSuperAdmin,
):
    target_date = payload.run_date or date.today()
    results = await scheduler_service.generate_automatic_payrolls(db, target_date)
    return envelope(
        data=results,
        message=f"Generación automática ejecutada para {target_date.isoformat()}",
    )
