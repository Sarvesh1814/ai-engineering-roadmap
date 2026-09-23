from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any

from scripts.feedback_db import save_feedback, get_feedback_stats, init_feedback_table
from config import get_logger

router = APIRouter(prefix="/api/v1", tags=["feedback"])
logger = get_logger("api.feedback")


class FeedbackRequest(BaseModel):
    request_id: str = Field(..., description="Request ID from /resolve response")
    solution_useful: bool | None = Field(default=None, description="Was the solution useful?")
    tickets_relevant: bool | None = Field(default=None, description="Were the cited tickets relevant?")
    next_steps_solved: bool | None = Field(default=None, description="Did next steps solve the issue?")
    correct_ticket_ids: list[str] | None = Field(default=None, description="Correct ticket IDs if different")
    comments: str | None = Field(default=None, description="Free-form feedback")


class FeedbackResponse(BaseModel):
    status: str
    feedback_id: int


class FeedbackStatsResponse(BaseModel):
    total_feedback: int
    solution_useful_rate: float
    tickets_relevant_rate: float
    next_steps_solved_rate: float


@router.on_event("startup")
async def startup():
    init_feedback_table()


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(feedback: FeedbackRequest):
    """
    Submit human feedback for a resolution.
    
    This feeds continuous evaluation and golden dataset expansion.
    """
    try:
        feedback_id = save_feedback(
            request_id=feedback.request_id,
            solution_useful=feedback.solution_useful,
            tickets_relevant=feedback.tickets_relevant,
            next_steps_solved=feedback.next_steps_solved,
            correct_ticket_ids=feedback.correct_ticket_ids,
            comments=feedback.comments,
        )
        
        logger.info("Feedback received", extra={
            "metadata": {
                "request_id": feedback.request_id,
                "feedback_id": feedback_id,
                "solution_useful": feedback.solution_useful,
                "tickets_relevant": feedback.tickets_relevant,
            }
        })
        
        return FeedbackResponse(status="saved", feedback_id=feedback_id)
        
    except Exception as e:
        logger.error(f"Failed to save feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save feedback: {str(e)}")


@router.get("/feedback/stats", response_model=FeedbackStatsResponse)
async def feedback_stats():
    """Get aggregate feedback statistics."""
    stats = get_feedback_stats()
    return FeedbackStatsResponse(**stats)