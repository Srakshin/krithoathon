"""Scheduler for the Horizon pipeline.

Uses APScheduler (BlockingScheduler) to run the pipeline automatically
every day at 08:00 AM via a cron trigger.
"""

import logging
from apscheduler.schedulers.blocking import BlockingScheduler

from src.cli import main as run_pipeline

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def scheduled_job() -> None:
    """Wrapper executed by the scheduler on every trigger."""
    logger.info("⏰ Scheduled job started — running Horizon pipeline...")
    try:
        run_pipeline()
        logger.info("✅ Pipeline completed successfully.")
    except Exception:
        logger.exception("❌ Pipeline failed with an error.")


if __name__ == "__main__":
    scheduler = BlockingScheduler()

    # Run every day at 08:00 AM
    scheduler.add_job(
        scheduled_job,
        trigger="cron",
        hour=8,
        minute=0,
        id="horizon_daily_run",
    )

    logger.info("🗓️  Scheduler started — pipeline will run daily at 08:00 AM.")
    logger.info("Press Ctrl+C to exit.\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Scheduler shut down.")
