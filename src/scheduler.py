"""
Email Processing Scheduler Module

Provides background scheduling for automatic email processing using APScheduler.
Automatically calls the email processing logic at configurable intervals.
"""

import logging
from datetime import datetime
from typing import Optional, Callable
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import os

# Configure logging
logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[BackgroundScheduler] = None
_job_id = "process_emails_job"
_processing_function: Optional[Callable] = None
_last_run_time: Optional[datetime] = None
_last_run_result: Optional[dict] = None


def initialize_scheduler(processing_function: Callable) -> None:
    """
    Initialize the scheduler with the processing function.

    Args:
        processing_function: Async function to call for processing emails.
                           Should return a dict with processing results.
    """
    global _scheduler, _processing_function

    if _scheduler is not None:
        logger.warning("Scheduler already initialized")
        return

    _processing_function = processing_function
    _scheduler = BackgroundScheduler(
        timezone="UTC",
        job_defaults={
            'coalesce': True,  # If job is late, run once instead of multiple times
            'max_instances': 1  # Only one instance of job can run at a time
        }
    )

    logger.info("Scheduler initialized successfully")


async def _job_wrapper():
    """
    Internal wrapper for the scheduled job.
    Handles error catching, logging, and state tracking.
    """
    global _last_run_time, _last_run_result

    try:
        logger.info("[Scheduler] Processing new emails...")
        _last_run_time = datetime.utcnow()

        # Call the processing function
        result = await _processing_function()
        _last_run_result = result

        # Log results
        processed = result.get("processed", 0)
        if processed > 0:
            categories = result.get("categories", {})
            category_str = ", ".join([f"{cat}={count}" for cat, count in categories.items()])
            logger.info(f"[Scheduler] Processed {processed} emails: {category_str}")
        else:
            logger.info("[Scheduler] No new emails to process")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[Scheduler] Error during processing: {error_msg}")
        _last_run_result = {"error": error_msg, "processed": 0}

        # Check for specific error conditions
        if "Not authenticated" in error_msg or "Token expired" in error_msg:
            logger.warning("[Scheduler] Token expired or missing, skipping processing")
        # Don't crash - let scheduler continue


def _sync_job_wrapper():
    """
    Synchronous wrapper that runs the async job in an event loop.
    Required because APScheduler doesn't natively support async jobs.
    """
    import asyncio

    # Get or create event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Run the async job
    loop.run_until_complete(_job_wrapper())


def start_scheduler(interval_seconds: int = 60) -> dict:
    """
    Start the background scheduler with specified interval.

    Args:
        interval_seconds: Time between processing runs (minimum 10 seconds, default 60)

    Returns:
        Dict with status message and configuration

    Raises:
        RuntimeError: If scheduler not initialized
        ValueError: If interval is less than minimum
    """
    global _scheduler

    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call initialize_scheduler() first.")

    # Enforce minimum interval
    MIN_INTERVAL = 10
    if interval_seconds < MIN_INTERVAL:
        raise ValueError(f"Interval must be at least {MIN_INTERVAL} seconds")

    # Check if already running
    if _scheduler.running:
        # Remove existing job
        try:
            _scheduler.remove_job(_job_id)
            logger.info("[Scheduler] Removed existing job for restart")
        except Exception:
            pass  # Job doesn't exist

    # Add the job with interval trigger
    _scheduler.add_job(
        func=_sync_job_wrapper,
        trigger=IntervalTrigger(seconds=interval_seconds),
        id=_job_id,
        name="Process New Emails",
        replace_existing=True
    )

    # Start scheduler if not already running
    if not _scheduler.running:
        _scheduler.start()
        logger.info(f"[Scheduler] Started - processing every {interval_seconds}s")
    else:
        logger.info(f"[Scheduler] Restarted with new interval - processing every {interval_seconds}s")

    return {
        "status": "started",
        "interval_seconds": interval_seconds,
        "next_run": _get_next_run_time()
    }


def stop_scheduler() -> dict:
    """
    Stop the background scheduler.

    Returns:
        Dict with status message

    Raises:
        RuntimeError: If scheduler not initialized
    """
    global _scheduler

    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized")

    if not _scheduler.running:
        logger.warning("[Scheduler] Scheduler is not running")
        return {"status": "not_running", "message": "Scheduler was not running"}

    # Remove the job
    try:
        _scheduler.remove_job(_job_id)
    except Exception:
        pass  # Job doesn't exist

    # Note: We don't call _scheduler.shutdown() because that would
    # prevent restart. We just remove the job.
    logger.info("[Scheduler] Stopped")

    return {"status": "stopped", "message": "Scheduler stopped successfully"}


def get_scheduler_status() -> dict:
    """
    Get current scheduler status and statistics.

    Returns:
        Dict with scheduler state, configuration, and last run info
    """
    global _scheduler, _last_run_time, _last_run_result

    if _scheduler is None:
        return {
            "running": False,
            "error": "Scheduler not initialized"
        }

    is_running = _scheduler.running

    # Get job info if exists
    next_run = None
    interval = None

    if is_running:
        try:
            job = _scheduler.get_job(_job_id)
            if job:
                next_run = _get_next_run_time()
                # Extract interval from trigger
                if hasattr(job.trigger, 'interval'):
                    interval = int(job.trigger.interval.total_seconds())
        except Exception as e:
            logger.debug(f"Could not get job info: {e}")

    status = {
        "running": is_running,
        "interval_seconds": interval,
        "next_run": next_run,
        "last_run": _last_run_time.isoformat() + "Z" if _last_run_time else None,
    }

    # Include last run results if available
    if _last_run_result:
        status["last_run_result"] = _last_run_result

    return status


def shutdown_scheduler() -> None:
    """
    Shutdown the scheduler completely (called on app shutdown).
    This will stop all jobs and release resources.
    """
    global _scheduler

    if _scheduler is None:
        return

    if _scheduler.running:
        logger.info("[Scheduler] Shutting down scheduler...")
        _scheduler.shutdown(wait=True)
        logger.info("[Scheduler] Shutdown complete")

    _scheduler = None


def _get_next_run_time() -> Optional[str]:
    """
    Get the next scheduled run time.

    Returns:
        ISO 8601 timestamp string or None if not scheduled
    """
    global _scheduler

    if _scheduler is None or not _scheduler.running:
        return None

    try:
        job = _scheduler.get_job(_job_id)
        if job and job.next_run_time:
            # Convert to UTC and format as ISO 8601
            return job.next_run_time.isoformat() + "Z"
    except Exception as e:
        logger.debug(f"Could not get next run time: {e}")

    return None


def get_default_interval() -> int:
    """
    Get the default polling interval from environment or use hardcoded default.

    Returns:
        Interval in seconds (default 60)
    """
    try:
        env_interval = os.getenv("POLLING_INTERVAL")
        if env_interval:
            interval = int(env_interval)
            # Enforce minimum
            if interval < 10:
                logger.warning(f"POLLING_INTERVAL {interval}s is below minimum 10s, using 10s")
                return 10
            return interval
    except (ValueError, TypeError):
        logger.warning("Invalid POLLING_INTERVAL in environment, using default")

    return 60  # Default 60 seconds
