"""Automatic payroll scheduler configuration (APScheduler)."""

import logging
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db.session import AsyncSessionLocal
from app.services import scheduler_service

logger = logging.getLogger("nomiapp.scheduler")

scheduler = AsyncIOScheduler()


def _configure_logger() -> None:
    """Makes the scheduler logger use uvicorn's handlers.

    Without this, INFO messages are lost because uvicorn does not add a handler
    to the root logger. If the app is not running under uvicorn, propagation is
    left as-is.
    """
    # The real handler is on the "uvicorn" logger; "uvicorn.error" only propagates.
    uvicorn_logger = logging.getLogger("uvicorn")
    if uvicorn_logger.handlers and not logger.handlers:
        for handler in uvicorn_logger.handlers:
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False


async def job_generate_automatic_payrolls() -> list[dict]:
    """Daily job: generates the payrolls due today.

    Opens its own database session (independent of the request cycle).
    """
    async with AsyncSessionLocal() as db:
        results = await scheduler_service.generate_automatic_payrolls(
            db, date.today()
        )
    generated = [r for r in results if r.get("status") == "generated"]
    logger.info(
        "[scheduler] Automatic payroll job finished: %d generated of %d companies evaluated",
        len(generated),
        len(results),
    )
    return results


def start_scheduler() -> None:
    _configure_logger()
    scheduler.add_job(
        job_generate_automatic_payrolls,
        CronTrigger(hour=6, minute=0),  # 6 AM daily
        id="generate_payrolls",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started (job 'generate_payrolls' at 06:00)")


def stop_scheduler() -> None:
    scheduler.shutdown()
    logger.info("Scheduler stopped")
