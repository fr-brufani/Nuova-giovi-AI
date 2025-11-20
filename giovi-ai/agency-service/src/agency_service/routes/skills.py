from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from agency_service.firestore import add_timestamps, get_client, serialize_document
from agency_service.models import SkillCreate, SkillResponse

from .dependencies import require_agency_id

router = APIRouter()


@router.get("/", response_model=List[SkillResponse])
def list_skills(agency_id: str = Depends(require_agency_id)):
    client = get_client()
    agency_docs = (
        client.collection("cleaningSkills")
        .where("agencyId", "==", agency_id)
        .order_by("name")
        .stream()
    )
    global_docs = (
        client.collection("cleaningSkills")
        .where("agencyId", "==", None)
        .order_by("name")
        .stream()
    )
    return [serialize_document(doc) for doc in agency_docs] + [
        serialize_document(doc) for doc in global_docs
    ]


@router.post("/", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
def create_skill(request: SkillCreate, agency_id: str = Depends(require_agency_id)):
    client = get_client()
    data = request.model_dump(by_alias=True)
    data["agencyId"] = agency_id
    doc = client.collection("cleaningSkills").document()
    doc.set(add_timestamps(data))
    return serialize_document(doc.get())

