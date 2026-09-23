from typing import Any
from pydantic import BaseModel, Field


class ResolveRequest(BaseModel):
    problem: str = Field(..., min_length=1, max_length=8192, description="Problem description to resolve")
    filter: dict[str, Any] | None = Field(default=None, description="Optional metadata filters")


class SourceInfo(BaseModel):
    ticket_id: str
    score: float


class ProblemUnderstanding(BaseModel):
    technology: list[str] = Field(default_factory=list)
    error_codes: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)


class ResolveResponse(BaseModel):
    request_id: str
    status: str
    problem_understanding: ProblemUnderstanding
    solution: str | None
    next_steps: list[str] = Field(default_factory=list)
    relevant_ticket_ids: list[str] = Field(default_factory=list)
    confidence: float
    sources: list[SourceInfo] = Field(default_factory=list)


class HealthResponse(BaseModel):
    healthy: bool
    service: str
    message: str
    details: dict[str, Any] | None = None


class ReadinessResponse(BaseModel):
    ready: bool
    checks: dict[str, HealthResponse]