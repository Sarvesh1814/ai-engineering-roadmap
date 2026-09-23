import argparse
import time
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config import get_logger, get_settings
from scripts.db import fetch_tickets_to_resolve, resolve_ticket


def build_problem_text(ticket: dict) -> str:
    """Build problem text from all available ticket fields."""
    parts = []
    for key, value in ticket.items():
        if value and str(value).strip() and key not in ("id", "hasUpdates"):
            parts.append(f"{key}: {value}")
    return "\n".join(parts)


def run_polling(once: bool = False, interval: int = 60):
    """Poll for tickets with hasUpdates='Yes' and resolve them."""
    settings = get_settings()
    logger = get_logger("polling")
    view_name = settings.mysql_resolver_view

    logger.info("Starting ticket resolution polling", extra={
        "metadata": {
            "view": view_name, 
            "interval_seconds": interval, 
            "once": once,
            "mysql_host": settings.mysql_host,
            "mysql_port": settings.mysql_port,
            "mysql_database": settings.mysql_database,
            "qdrant_host": settings.qdrant_host,
            "qdrant_port": settings.qdrant_port,
            "llm_provider": settings.llm_provider,
            "llm_model": settings.llm_model_name,
        }
    })

    while True:
        try:
            tickets = fetch_tickets_to_resolve(view_name)
            logger.info(f"Found {len(tickets)} tickets to resolve")

            for ticket in tickets:
                record_id = ticket.get("id")
                if not record_id:
                    logger.warning("Ticket missing 'id' field, skipping", extra={"metadata": ticket})
                    continue

                problem_text = build_problem_text(ticket)
                if not problem_text.strip():
                    logger.warning(f"No problem text for record_id={record_id}, skipping")
                    continue

                logger.info(f"Resolving ticket record_id={record_id}", extra={
                    "metadata": {"record_id": record_id, "display_id": ticket.get("display_id")}
                })

                try:
                    result = resolve_ticket(record_id, problem_text)
                    logger.info(f"Resolved ticket record_id={record_id}", extra={"metadata": result})
                except Exception as e:
                    logger.error(f"Failed to resolve ticket record_id={record_id}: {e}", extra={
                        "metadata": {"record_id": record_id, "error": str(e), "error_type": type(e).__name__}
                    })

        except Exception as e:
            logger.error(f"Polling cycle error: {e}", extra={"metadata": {"error": str(e), "error_type": type(e).__name__}})

        if once:
            logger.info("Single run complete, exiting")
            break

        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="ServiceNow ticket resolution poller")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval in seconds")
    args = parser.parse_args()

    run_polling(once=args.once, interval=args.interval)


if __name__ == "__main__":
    main()