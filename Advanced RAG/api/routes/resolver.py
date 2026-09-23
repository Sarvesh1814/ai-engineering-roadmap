from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
import uuid
import json

from api.schemas import ResolveRequest, ResolveResponse
from resolver.graph import ResolverAgent
from config import get_logger, get_settings

router = APIRouter(prefix="/api/v1", tags=["resolver"])
logger = get_logger("api.resolver")


def _get_agent(request: Request) -> ResolverAgent:
    """Retrieve the shared ResolverAgent from app state (initialized in lifespan)."""
    return request.app.state.resolver_agent


@router.post("/resolve", response_model=ResolveResponse)
async def resolve_problem(request: ResolveRequest, http_request: Request):
    """
    Resolve a problem using the agentic RAG pipeline.

    Returns a grounded solution with relevant historical ticket references.
    """
    request_id = str(uuid.uuid4())

    logger.info(
        f"Received resolve request",
        extra={"metadata": {"request_id": request_id, "problem_length": len(request.problem)}}
    )

    try:
        agent = _get_agent(http_request)
        result = agent.resolve(request.problem, request_id)

        if request.filter:
            logger.debug(f"Filter provided but not yet implemented: {request.filter}")

        response = ResolveResponse(**result)

        logger.info(
            f"Resolve completed",
            extra={"metadata": {"request_id": request_id, "status": result["status"], "confidence": result["confidence"]}}
        )

        return response

    except Exception as e:
        logger.error(
            f"Resolve failed",
            extra={"metadata": {"request_id": request_id, "error": str(e)}}
        )
        raise HTTPException(status_code=500, detail=f"Resolution failed: {str(e)}")


@router.post("/resolve/stream")
async def resolve_problem_stream(request: ResolveRequest, http_request: Request):
    """
    Stream the resolution process using Server-Sent Events.

    Events:
    - status: Current pipeline stage
    - token: Generated token (when streaming LLM)
    - sources: Relevant ticket IDs
    - complete: Final result with confidence
    """
    request_id = str(uuid.uuid4())

    logger.info(
        f"Received streaming resolve request",
        extra={"metadata": {"request_id": request_id}}
    )

    async def event_generator():
        try:
            agent = _get_agent(http_request)

            yield {"event": "status", "data": json.dumps({"stage": "understand", "request_id": request_id})}

            yield {"event": "status", "data": json.dumps({"stage": "retrieve", "request_id": request_id})}

            yield {"event": "status", "data": json.dumps({"stage": "rerank", "request_id": request_id})}

            yield {"event": "status", "data": json.dumps({"stage": "evidence_builder", "request_id": request_id})}

            yield {"event": "status", "data": json.dumps({"stage": "verify", "request_id": request_id})}

            yield {"event": "status", "data": json.dumps({"stage": "generate", "request_id": request_id})}

            result = agent.resolve(request.problem, request_id)

            if result.get("relevant_ticket_ids"):
                yield {"event": "sources", "data": json.dumps({"ticket_ids": result["relevant_ticket_ids"]})}

            if result.get("solution"):
                for token in result["solution"].split():
                    yield {"event": "token", "data": json.dumps({"text": token + " "})}

            final_data = {
                "confidence": result["confidence"],
                "status": result["status"],
                "next_steps": result.get("next_steps", []),
                "relevant_ticket_ids": result.get("relevant_ticket_ids", []),
            }
            yield {"event": "complete", "data": json.dumps(final_data)}

        except Exception as e:
            logger.error(f"Streaming resolve failed: {e}")
            yield {"event": "error", "data": json.dumps({"error": str(e)})}

    return EventSourceResponse(event_generator())