from fastapi import APIRouter
from config.health import HealthChecker
from api.schemas import HealthResponse, ReadinessResponse

router = APIRouter(prefix="/api/v1", tags=["health"])
health_checker = HealthChecker()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Liveness probe - returns whether the application is running.
    Does not check external dependencies.
    """
    result = health_checker.liveness()
    return HealthResponse(
        healthy=result.healthy,
        service=result.service,
        message=result.message,
        details=result.details,
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check():
    """
    Readiness probe - checks all external dependencies.
    Returns 503 if any dependency is unhealthy.
    """
    ready, checks = health_checker.readiness()
    
    check_responses = {
        name: HealthResponse(
            healthy=check.healthy,
            service=check.service,
            message=check.message,
            details=check.details,
        )
        for name, check in checks.items()
    }
    
    return ReadinessResponse(
        ready=ready,
        checks=check_responses,
    )