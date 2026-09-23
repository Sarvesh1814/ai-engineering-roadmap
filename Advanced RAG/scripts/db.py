from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from typing import Any
import json

from config import get_settings, get_logger


def get_engine():
    settings = get_settings()
    password = settings.mysql_password or ""
    DATABASE_URL = (
        f"mysql+pymysql://{settings.mysql_user}:{password}@"
        f"{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}"
    )
    logger = get_logger("polling.db.engine")
    logger.debug("Creating DB engine", extra={"metadata": {"host": settings.mysql_host, "port": settings.mysql_port, "database": settings.mysql_database}})
    return create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


def fetch_tickets_to_resolve(view_name: str | None = None) -> list[dict[str, Any]]:
    """Fetch tickets where hasUpdates = 'Yes' from the configured view."""
    settings = get_settings()
    view = view_name or settings.mysql_resolver_view
    logger = get_logger("polling.db")
    engine = get_engine()

    query = f"SELECT * FROM `{view}` WHERE `hasUpdates` = 'Yes'"
    logger.debug(f"Fetching tickets from view", extra={"metadata": {"view": view}})
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            columns = result.keys()
            tickets = [dict(zip(columns, row)) for row in result.fetchall()]
            logger.info(f"Fetched {len(tickets)} tickets to resolve", extra={"metadata": {"view": view, "count": len(tickets)}})
            return tickets
    except OperationalError as e:
        logger.error("Database connection failed", extra={"metadata": {"host": settings.mysql_host, "port": settings.mysql_port, "database": settings.mysql_database, "error": str(e), "error_type": type(e).__name__}})
        raise
    except SQLAlchemyError as e:
        logger.error("Database query failed", extra={"metadata": {"view": view, "error": str(e), "error_type": type(e).__name__}})
        raise


def update_extra_field(record_id: int, field_id: str, field_value: str) -> int:
    """Update field_value in ops_extra_fields for given record_id and field_id."""
    settings = get_settings()
    logger = get_logger("polling.db")
    engine = get_engine()

    logger.debug(f"Updating extra_field", extra={"metadata": {"record_id": record_id, "field_id": field_id, "value_length": len(field_value)}})
    try:
        with engine.connect() as conn:
            with conn.begin():
                result = conn.execute(
                    text(
                        "UPDATE `ops_extra_fields` "
                        "SET `field_value` = :value "
                        "WHERE `record_id` = :rid AND `field_id` = :fid"
                    ),
                    {"value": field_value, "rid": record_id, "fid": field_id},
                )
                logger.debug(f"Updated extra_field", extra={"metadata": {"record_id": record_id, "field_id": field_id, "rows_affected": result.rowcount}})
                return result.rowcount
    except OperationalError as e:
        logger.error("Database connection failed updating extra_field", extra={"metadata": {"record_id": record_id, "field_id": field_id, "error": str(e), "error_type": type(e).__name__}})
        raise
    except SQLAlchemyError as e:
        logger.error("Database query failed updating extra_field", extra={"metadata": {"record_id": record_id, "field_id": field_id, "error": str(e), "error_type": type(e).__name__}})
        raise


def mark_ticket_processed(record_id: int) -> int:
    """Set hasUpdates = 'No' in ops_workitem for the given record_id."""
    settings = get_settings()
    logger = get_logger("polling.db")
    engine = get_engine()

    logger.debug(f"Marking ticket processed", extra={"metadata": {"record_id": record_id}})
    try:
        with engine.connect() as conn:
            with conn.begin():
                result = conn.execute(
                    text("UPDATE `ops_workitem` SET `hasUpdates` = 'No' WHERE `id` = :rid"),
                    {"rid": record_id},
                )
                logger.debug(f"Marked ticket processed", extra={"metadata": {"record_id": record_id, "rows_affected": result.rowcount}})
                return result.rowcount
    except OperationalError as e:
        logger.error("Database connection failed marking ticket processed", extra={"metadata": {"record_id": record_id, "error": str(e), "error_type": type(e).__name__}})
        raise
    except SQLAlchemyError as e:
        logger.error("Database query failed marking ticket processed", extra={"metadata": {"record_id": record_id, "error": str(e), "error_type": type(e).__name__}})
        raise


def resolve_ticket(record_id: int, problem_text: str) -> dict:
    """
    Process a single ticket: resolve, persist results, mark done.
    ONLY updates DB on successful resolution with valid content.
    On any failure (LLM unavailable, empty result, exception), leaves ticket untouched for retry.
    Returns dict with status info.
    """
    from resolver.graph import ResolverAgent
    from config import get_logger
    import uuid

    logger = get_logger("polling.db")
    request_id = str(uuid.uuid4())

    try:
        agent = ResolverAgent()
        result = agent.resolve(problem_text, request_id)

        # Validate result - must have meaningful content
        status = result.get("status", "")
        solution = result.get("solution", "") or ""
        confidence = result.get("confidence", 0.0)
        relevant_tickets = result.get("relevant_ticket_ids", [])

        # Reject if: no reliable solution, empty solution, very low confidence
        if status == "no_reliable_solution":
            logger.warning(f"Resolver returned no_reliable_solution for record_id={record_id}, skipping DB update for retry")
            return {
                "record_id": record_id,
                "request_id": request_id,
                "status": "skipped_no_solution",
                "confidence": confidence,
                "reason": "Resolver found no reliable solution",
                "db_updated": False,
            }

        if not solution.strip():
            logger.warning(f"Resolver returned empty solution for record_id={record_id}, skipping DB update for retry")
            return {
                "record_id": record_id,
                "request_id": request_id,
                "status": "skipped_empty_solution",
                "confidence": confidence,
                "reason": "Generated solution is empty",
                "db_updated": False,
            }

        if confidence < 0.3:
            logger.warning(f"Resolver confidence too low ({confidence}) for record_id={record_id}, skipping DB update for retry")
            return {
                "record_id": record_id,
                "request_id": request_id,
                "status": "skipped_low_confidence",
                "confidence": confidence,
                "reason": f"Confidence {confidence} below threshold 0.3",
                "db_updated": False,
            }

        # Prepare values for extra_fields
        similar_tickets_json = json.dumps(relevant_tickets)
        resolution_steps = solution
        if result.get("next_steps"):
            resolution_steps += "\n\nNext Steps:\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(result["next_steps"]))

        # Update Similar_Ticket_IDs
        updated_similar = update_extra_field(record_id, "Similar_Ticket_IDs", similar_tickets_json)
        # Update Resolution_Steps
        updated_resolution = update_extra_field(record_id, "Resolution_Steps", resolution_steps)

        if updated_similar == 0 or updated_resolution == 0:
            logger.error(f"Failed to update extra_fields for record_id={record_id}, NOT marking ticket processed")
            return {
                "record_id": record_id,
                "request_id": request_id,
                "status": "failed_db_update",
                "confidence": confidence,
                "reason": "Failed to write to ops_extra_fields",
                "db_updated": False,
            }

        # Only mark ticket as processed AFTER successful extra_fields update
        marked = mark_ticket_processed(record_id)
        if marked == 0:
            logger.error(f"Failed to mark ticket processed for record_id={record_id}")
            return {
                "record_id": record_id,
                "request_id": request_id,
                "status": "failed_mark_processed",
                "confidence": confidence,
                "reason": "Failed to update hasUpdates in ops_workitem",
                "db_updated": False,
            }

        logger.info(f"Successfully resolved and persisted ticket record_id={record_id}")
        return {
            "record_id": record_id,
            "request_id": request_id,
            "status": "success",
            "confidence": confidence,
            "similar_tickets_updated": True,
            "resolution_steps_updated": True,
            "ticket_marked": True,
            "db_updated": True,
        }

    except Exception as e:
        logger.error(f"Exception resolving ticket record_id={record_id}: {e}", extra={"metadata": {"record_id": record_id, "error": str(e)}})
        return {
            "record_id": record_id,
            "request_id": request_id,
            "status": "error",
            "confidence": 0.0,
            "reason": f"Exception: {str(e)}",
            "db_updated": False,
        }