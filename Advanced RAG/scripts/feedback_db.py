from sqlalchemy import create_engine, text
from typing import Any
from datetime import datetime

from config.settings import get_settings


def get_engine():
    settings = get_settings()
    password = settings.mysql_password or ""
    DATABASE_URL = (
        f"mysql+pymysql://{settings.mysql_user}:{password}@"
        f"{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}"
    )
    return create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


def init_feedback_table() -> None:
    """Create feedback table if not exists."""
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS `resolver_feedback` (
                    `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
                    `request_id` VARCHAR(64) NOT NULL,
                    `solution_useful` BOOLEAN,
                    `tickets_relevant` BOOLEAN,
                    `next_steps_solved` BOOLEAN,
                    `correct_ticket_ids` JSON,
                    `comments` TEXT,
                    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX `idx_request_id` (`request_id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """))


def save_feedback(
    request_id: str,
    solution_useful: bool | None = None,
    tickets_relevant: bool | None = None,
    next_steps_solved: bool | None = None,
    correct_ticket_ids: list[str] | None = None,
    comments: str | None = None,
) -> int:
    """Save human feedback to database."""
    engine = get_engine()
    with engine.connect() as conn:
        with conn.begin():
            result = conn.execute(
                text("""
                    INSERT INTO `resolver_feedback` 
                    (`request_id`, `solution_useful`, `tickets_relevant`, `next_steps_solved`, `correct_ticket_ids`, `comments`)
                    VALUES (:request_id, :useful, :relevant, :solved, :correct_ids, :comments)
                """),
                {
                    "request_id": request_id,
                    "useful": solution_useful,
                    "relevant": tickets_relevant,
                    "solved": next_steps_solved,
                    "correct_ids": json.dumps(correct_ticket_ids) if correct_ticket_ids else None,
                    "comments": comments,
                },
            )
            return result.lastrowid


def get_feedback_stats() -> dict[str, Any]:
    """Get aggregate feedback statistics."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total,
                AVG(CASE WHEN solution_useful = 1 THEN 1 ELSE 0 END) as useful_rate,
                AVG(CASE WHEN tickets_relevant = 1 THEN 1 ELSE 0 END) as relevant_rate,
                AVG(CASE WHEN next_steps_solved = 1 THEN 1 ELSE 0 END) as solved_rate
            FROM `resolver_feedback`
        """))
        row = result.fetchone()
        return {
            "total_feedback": row[0] or 0,
            "solution_useful_rate": float(row[1] or 0),
            "tickets_relevant_rate": float(row[2] or 0),
            "next_steps_solved_rate": float(row[3] or 0),
        }


import json