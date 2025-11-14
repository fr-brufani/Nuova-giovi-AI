from fastapi import APIRouter, status

router = APIRouter()


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    tags=["health"],
)
async def get_live_status() -> dict[str, str]:
    return {"status": "ok"}


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    tags=["health"],
)
async def get_readiness_status() -> dict[str, str]:
    return {"status": "ready"}

