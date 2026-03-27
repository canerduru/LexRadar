"""
Scheduler executing the Pipeline Orchestrator on a schedule.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import structlog

from config.settings import Settings, get_settings
from radar.orchestrator import PipelineOrchestrator


class PipelineScheduler:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._logger = structlog.get_logger()
        self._orchestrator = PipelineOrchestrator(self._settings)
        # apscheduler configuration
        self._scheduler = AsyncIOScheduler(timezone=self._settings.SCHEDULE_TIMEZONE)
        
    async def _catch_up(self) -> None:
        """Runs immediately once if last run was > 23 hours ago"""
        log_file = "data/pipeline_runs.jsonl"
        if not os.path.exists(log_file):
            self._logger.info("Initializing first run catch up.")
            await self._orchestrator.run_full_pipeline(days_back=1)
            return

        last_time = None
        try:
            with open(log_file, "r") as f:
                lines = f.readlines()
                if lines:
                    last_run = json.loads(lines[-1].strip())
                    last_time_str = last_run.get("started_at")
                    if last_time_str:
                        last_time = datetime.fromisoformat(last_time_str)
        except Exception:
            pass

        if not last_time:
            self._logger.info("No valid previous run found. Running catch up.")
            await self._orchestrator.run_full_pipeline(days_back=1)
            return

        now = datetime.now(timezone.utc)
        diff_hours = (now - last_time).total_seconds() / 3600.0
        
        if diff_hours > 23:
            self._logger.info(f"Last run was {diff_hours:.1f} hours ago. Running catch up.")
            await self._orchestrator.run_full_pipeline(days_back=1)
        else:
            self._logger.info(f"Last run was {diff_hours:.1f} hours ago. Yielding to scheduler.")

    async def _run_job(self) -> None:
        self._logger.info("Executing scheduled pipeline job")
        try:
            await self._orchestrator.run_full_pipeline(days_back=1)
        except Exception as e:
            self._logger.error("Scheduled job failed", error=str(e))

    def _shutdown(self, signame: str) -> None:
        self._logger.info(f"Received {signame}. Shutting down gracefully...")
        self._scheduler.shutdown()
        
    async def start(self) -> None:
        # Check catch-up synchronously prior to cron start
        await self._catch_up()

        trigger = CronTrigger(
            hour=self._settings.SCHEDULE_HOUR,
            timezone=self._settings.SCHEDULE_TIMEZONE
        )
        
        self._scheduler.add_job(
            self._run_job,
            trigger=trigger,
            id="daily_pipeline_run",
            replace_existing=True,
            max_instances=1
        )

        self._scheduler.start()
        
        self._logger.info(
            "Scheduler active.", 
            hour=self._settings.SCHEDULE_HOUR, 
            timezone=self._settings.SCHEDULE_TIMEZONE
        )

        loop = asyncio.get_running_loop()
        for signame in {'SIGINT', 'SIGTERM'}:
            try:
                loop.add_signal_handler(
                    getattr(signal, signame),
                    lambda s=signame: self._shutdown(s)
                )
            except NotImplementedError:
                pass # Windows fallback

        # Sleep indefinitely
        while self._scheduler.running:
            await asyncio.sleep(1)


def main() -> None:
    scheduler = PipelineScheduler()
    asyncio.run(scheduler.start())

if __name__ == "__main__":
    main()
