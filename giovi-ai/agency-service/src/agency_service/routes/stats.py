from datetime import datetime
from typing import Final

from fastapi import APIRouter, Depends, HTTPException, status
from google.cloud import firestore

from agency_service.firestore import get_client
from agency_service.models import AgencyStats

from .dependencies import require_agency_id

router = APIRouter()

_STAFF_COLLECTION: Final = "cleaningStaff"
_JOBS_COLLECTION: Final = "cleaningJobs"
_ROUTES_COLLECTION: Final = "cleaningRoutes"


def _count(query: firestore.Query) -> int:
    return len(list(query.stream()))


@router.get("/stats", response_model=AgencyStats)
def get_agency_stats(agency_id: str = Depends(require_agency_id)):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    try:
        client = get_client()
        staff_active = _count(
            client.collection(_STAFF_COLLECTION)
            .where("agencyId", "==", agency_id)
            .where("status", "==", "active")
        )
        jobs_today = _count(
            client.collection(_JOBS_COLLECTION)
            .where("agencyId", "==", agency_id)
            .where("scheduledDate", "==", today)
        )
        jobs_completed = _count(
            client.collection(_JOBS_COLLECTION)
            .where("agencyId", "==", agency_id)
            .where("scheduledDate", "==", today)
            .where("status", "==", "completed")
        )
        routes_optimized = _count(
            client.collection(_ROUTES_COLLECTION)
            .where("agencyId", "==", agency_id)
            .where("date", "==", today)
        )
        return AgencyStats(
            staff_active=staff_active,
            jobs_today=jobs_today,
            routes_optimized=routes_optimized,
            jobs_completed=jobs_completed,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unable to load stats: {exc}",
        ) from exc

