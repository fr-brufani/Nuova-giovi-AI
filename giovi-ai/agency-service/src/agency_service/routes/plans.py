from typing import List

from fastapi import APIRouter, Depends, Query
from google.cloud import firestore

from agency_service.config import settings
from agency_service.firestore import get_client, serialize_document
from agency_service.models import PlanRequest, PlanResponse
from agency_service.services.planning import generate_plan

from .dependencies import require_agency_id

router = APIRouter()


@router.get("/", response_model=List[PlanResponse])
def list_plans(
    agency_id: str = Depends(require_agency_id),
    limit: int = Query(10, ge=1, le=50),
):
    client = get_client()
    query = (
        client.collection("cleaningPlans")
        .where("agencyId", "==", agency_id)
        .order_by("date", direction=firestore.Query.DESCENDING)
        .limit(limit)
    )
    docs = [serialize_document(doc) for doc in query.stream()]
    return docs


@router.post("/generate", response_model=PlanResponse)
def generate_daily_plan(request: PlanRequest, agency_id: str = Depends(require_agency_id)):
    # forza agencyId dalla sessione
    payload = request.model_dump()
    payload["agency_id"] = agency_id

    result = generate_plan(
        get_client(),
        agency_id=agency_id,
        date=request.date,
        plan_version=settings.default_plan_version,
    )

    plan_doc = get_client().collection("cleaningPlans").document(result["planId"]).get()
    serialized = serialize_document(plan_doc)
    return PlanResponse(**serialized)

