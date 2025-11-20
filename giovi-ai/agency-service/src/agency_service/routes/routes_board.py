from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from google.cloud import firestore

from agency_service.firestore import get_client, serialize_document
from agency_service.models import RouteResponse

from .dependencies import require_agency_id

router = APIRouter()


@router.get("/", response_model=List[RouteResponse])
def list_routes(
    agency_id: str = Depends(require_agency_id),
    date: Optional[str] = Query(None),
):
    client = get_client()
    query = (
        client.collection("cleaningRoutes")
        .where("agencyId", "==", agency_id)
        .order_by("date", direction=firestore.Query.DESCENDING)
    )
    if date:
        query = (
            client.collection("cleaningRoutes")
            .where("agencyId", "==", agency_id)
            .where("date", "==", date)
        )
    docs = query.stream()
    return [RouteResponse(**serialize_document(doc)) for doc in docs]

