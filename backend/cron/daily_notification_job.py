"""
Standalone Daily Notification Engine Cron Job.

Executes daily to evaluate all active students for:
- "Upcoming Exams" (milestones & assessment tasks in the next 7 days)
- "Unresolved Weak Topics" (sessions with study deficits and low completion rates)

Pushes alerts directly into the Supabase notifications table.

Usage:
    python backend/cron/daily_notification_job.py [--dry-run] [--user-id <uuid>]
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add backend directory to path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import get_db
from services.notification_engine import notification_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("DailyNotificationCron")


def main():
    parser = argparse.ArgumentParser(description="Automated Daily Notification Engine Dispatch")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate evaluation without inserting records into the database",
    )
    parser.add_argument(
        "--user-id",
        type=str,
        default=None,
        help="Optional specific student UUID to evaluate instead of all users",
    )
    args = parser.parse_args()

    logger.info("Initializing Notification Engine cron job (dry_run=%s)", args.dry_run)

    try:
        db = get_db()
    except Exception as exc:
        logger.error("Failed to initialize database client: %s", exc)
        sys.exit(1)

    if args.user_id:
        logger.info("Running targeted dispatch for student: %s", args.user_id)
        result = notification_engine.dispatch_for_student(
            user_id=args.user_id,
            db=db,
            dry_run=args.dry_run,
        )
        logger.info(
            "Student %s dispatch complete: %d weak topic alerts, %d exam alerts, %d total pushed.",
            args.user_id,
            result["weak_topic_alerts_count"],
            result["exam_alerts_count"],
            result["total_created"],
        )
    else:
        logger.info("Running full batch dispatch for all registered students...")
        result = notification_engine.run_daily_notification_dispatch(
            db=db,
            dry_run=args.dry_run,
        )
        logger.info("=" * 60)
        logger.info("DAILY NOTIFICATION DISPATCH SUMMARY")
        logger.info("Students Evaluated:           %d", result["students_evaluated"])
        logger.info("Students With New Alerts:     %d", result["students_with_alerts"])
        logger.info("Total Notifications Pushed:   %d", result["total_notifications_dispatched"])
        logger.info("Execution Duration:           %.3fs", result["execution_duration_seconds"])
        logger.info("=" * 60)


if __name__ == "__main__":
    main()

