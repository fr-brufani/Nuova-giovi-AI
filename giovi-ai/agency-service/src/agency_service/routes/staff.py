from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, status

from agency_service.firestore import add_timestamps, get_client, serialize_document
from agency_service.models import StaffCreate, StaffResponse, StaffUpdate

from .dependencies import require_agency_id

router = APIRouter()


@router.get("/", response_model=List[StaffResponse])
def list_staff(agency_id: str = Depends(require_agency_id)):
    client = get_client()
    docs = (
        client.collection("cleaningStaff")
        .where("agencyId", "==", agency_id)
        .order_by("displayName")
        .stream()
    )
    return [serialize_document(doc) for doc in docs]


@router.post("/", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
def create_staff(payload: StaffCreate, agency_id: str = Depends(require_agency_id)):
    client = get_client()
    # override agencyId from header to prevent spoof
    data = payload.model_dump(by_alias=True)
    data["agencyId"] = agency_id
    doc = client.collection("cleaningStaff").document()
    doc.set(add_timestamps(data))
    return serialize_document(doc.get())


@router.patch("/{staff_id}", response_model=StaffResponse)
def update_staff(
    staff_id: str = Path(..., min_length=6),
    payload: StaffUpdate = ...,
    agency_id: str = Depends(require_agency_id),
):
    client = get_client()
    doc_ref = client.collection("cleaningStaff").document(staff_id)
    snapshot = doc_ref.get()
    if not snapshot.exists or snapshot.to_dict().get("agencyId") != agency_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")
    update_data = payload.model_dump(by_alias=True, exclude_none=True)
    if not update_data:
        return serialize_document(snapshot)
    doc_ref.update(add_timestamps(update_data, is_update=True))
    return serialize_document(doc_ref.get())

