from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from agency_service.firestore import add_timestamps, get_client, serialize_document
from agency_service.models import JobCreate, JobResponse, JobUpdate

from .dependencies import require_agency_id

router = APIRouter()


@router.get("/", response_model=List[JobResponse])
def list_jobs(
    agency_id: str = Depends(require_agency_id),
    status_filter: Optional[str] = Query(None, alias="status"),
    scheduled_date: Optional[str] = Query(None, alias="scheduledDate"),
):
    client = get_client()
    query = client.collection("cleaningJobs").where("agencyId", "==", agency_id)
    if status_filter:
        query = query.where("status", "==", status_filter)
    if scheduled_date:
        query = query.where("scheduledDate", "==", scheduled_date)
    query = query.order_by("scheduledDate")
    docs = query.stream()
    return [serialize_document(doc) for doc in docs]


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, agency_id: str = Depends(require_agency_id)):
    client = get_client()
    data = payload.model_dump(by_alias=True)
    data["agencyId"] = agency_id
    doc = client.collection("cleaningJobs").document()
    doc.set(add_timestamps(data))
    return serialize_document(doc.get())


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(job_id: str, payload: JobUpdate, agency_id: str = Depends(require_agency_id)):
    client = get_client()
    doc_ref = client.collection("cleaningJobs").document(job_id)
    snapshot = doc_ref.get()
    if not snapshot.exists or snapshot.to_dict().get("agencyId") != agency_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    update_data = payload.model_dump(by_alias=True, exclude_none=True)
    if not update_data:
        return serialize_document(snapshot)
    doc_ref.update(add_timestamps(update_data, is_update=True))
    return serialize_document(doc_ref.get())

