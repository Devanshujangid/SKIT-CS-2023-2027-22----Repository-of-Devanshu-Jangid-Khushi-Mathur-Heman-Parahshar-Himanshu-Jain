"""
Standalone Midnight Leaderboard Evaluation Cron Job.

Executes every night at midnight to:
1. Re-evaluate student study hours and completion rates from active tasks.
2. Calculate updated dense rankings and dynamic goal statuses.
3. Refresh the cached leaderboard table (public.leaderboard_ranks).

Usage:
    python backend/cron/daily_leaderboard_job.py [--dry-run]
"""

import argparse
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import get_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("MidnightLeaderboardCron")


def refresh_leaderboard(dry_run: bool = False):
    logger.info("Starting Midnight Leaderboard Evaluation (dry_run=%s)", dry_run)
    db = get_db()

    if dry_run:
        # Dry run simulation: query view directly without table truncate/insert
        res = db.table("v_student_leaderboard").select("user_id, rank, display_name, actual_study_hours, completion_rate").execute()
        rows = res.data or []
        logger.info("[Dry Run] Evaluated %d student rankings successfully.", len(rows))
        return {
            "success": True,
            "dry_run": True,
            "evaluated_students": len(rows),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # Execute stored procedure on database
    try:
        rpc_res = db.rpc("refresh_leaderboard_rankings").execute()
        count = rpc_res.data if rpc_res.data is not None else 0
        logger.info("Successfully refreshed leaderboard rankings for %d active students.", count)
        return {
            "success": True,
            "dry_run": False,
            "evaluated_students": count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.warning("Database RPC refresh_leaderboard_rankings failed, falling back to manual refresh: %s", exc)
        # Fallback: Query view and upsert into leaderboard_ranks
        view_res = db.table("v_student_leaderboard").select("*").execute()
        rows = view_res.data or []

        if rows:
            db.table("leaderboard_ranks").upsert(rows, on_conflict="user_id").execute()

        logger.info("Manual refresh completed for %d student rankings.", len(rows))
        return {
            "success": True,
            "dry_run": False,
            "evaluated_students": len(rows),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


def main():
    parser = argparse.ArgumentParser(description="Midnight Leaderboard Evaluation Cron Job")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate ranking recalculation without database mutation",
    )
    args = parser.parse_args()

    result = refresh_leaderboard(dry_run=args.dry_run)
    logger.info("Cron job result: %s", result)


if __name__ == "__main__":
    main()

