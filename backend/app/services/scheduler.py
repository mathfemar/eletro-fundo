from __future__ import annotations

from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from ..config import settings
from ..db import session_scope
from .pricing_service import PricingService


scheduler = BackgroundScheduler(timezone='UTC')


def schedule_jobs() -> None:
    if scheduler.running:
        return

    pricing_service = PricingService()

    def sync_live_prices_job() -> None:
        with session_scope() as session:
            pricing_service.sync_live_prices(session)

    def sync_daily_history_job() -> None:
        end = date.today()
        start = end - timedelta(days=7)
        with session_scope() as session:
            pricing_service.sync_history(session, start, end)
            pricing_service.sync_dividends(session, start, end)

    if settings.enable_scheduler:
        scheduler.add_job(sync_live_prices_job, 'interval', minutes=settings.scheduler_live_minutes, id='live-30m', replace_existing=True)
        scheduler.add_job(sync_daily_history_job, 'cron', hour=1, minute=0, id='daily-history', replace_existing=True)
        scheduler.start()
