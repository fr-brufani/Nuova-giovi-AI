from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from firebase_admin import firestore
from pydantic import BaseModel, Field, field_validator

from ...dependencies.firebase import get_firestore_client
from ...repositories import ClientsRepository, PropertiesRepository, ReservationsRepository
from ...repositories.property_name_mappings import (
    PropertyMappingAction,
    PropertyNameMappingsRepository,
)

router = APIRouter()


class PropertyMappingResponse(BaseModel):
    id: str
    host_id: str = Field(..., alias="hostId")
    extracted_name: str = Field(..., alias="extractedName")
    action: PropertyMappingAction
    target_property_id: Optional[str] = Field(None, alias="targetPropertyId")
    notes: Optional[str] = None
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")

    @staticmethod
    def from_record(record) -> "PropertyMappingResponse":
        return PropertyMappingResponse(
            id=record.id,
            hostId=record.host_id,
            extractedName=record.extracted_name,
            action=record.action,
            targetPropertyId=record.target_property_id,
            notes=record.notes,
            createdAt=record.created_at,
            updatedAt=record.updated_at,
        )


class CreatePropertyMappingRequest(BaseModel):
    extracted_name: str = Field(..., alias="extractedName", min_length=1)
    action: PropertyMappingAction
    target_property_id: Optional[str] = Field(None, alias="targetPropertyId")
    notes: Optional[str] = None

    @field_validator("target_property_id")
    @classmethod
    def validate_target_property(cls, value: Optional[str], info):
        action = info.data.get("action")
        if action == "map" and not value:
            raise ValueError("targetPropertyId è obbligatorio per action=map")
        return value


class UpdatePropertyMappingRequest(BaseModel):
    extracted_name: Optional[str] = Field(None, alias="extractedName")
    action: Optional[PropertyMappingAction] = None
    target_property_id: Optional[str] = Field(None, alias="targetPropertyId")
    notes: Optional[str] = None

    @field_validator("target_property_id")
    @classmethod
    def validate_target_property(cls, value: Optional[str], info):
        action = info.data.get("action")
        if action == "map" and not value:
            raise ValueError("targetPropertyId è obbligatorio per action=map")
        return value


class ResolvePropertyMappingRequest(BaseModel):
    extracted_name: str = Field(..., alias="extractedName", min_length=1)
    action: PropertyMappingAction
    target_property_id: Optional[str] = Field(None, alias="targetPropertyId")
    notes: Optional[str] = None
    reassign_existing: bool = Field(False, alias="reassignExisting")
    delete_auto_property: bool = Field(False, alias="deleteAutoProperty")

    @field_validator("target_property_id")
    @classmethod
    def validate_target_property(cls, value: Optional[str], info):
        action = info.data.get("action")
        if action == "map" and not value:
            raise ValueError("targetPropertyId è obbligatorio per action=map")
        return value


class PropertyCandidateResponse(BaseModel):
    property_id: str = Field(..., alias="propertyId")
    name: str
    imported_from: Optional[str] = Field(None, alias="importedFrom")
    requires_review: bool = Field(False, alias="requiresReview")
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")


class ResolvePropertyMappingResponse(BaseModel):
    mapping: PropertyMappingResponse
    reassigned_reservations: int = Field(..., alias="reassignedReservations")
    deleted_properties: int = Field(..., alias="deletedProperties")


class PropertyMatchResponse(BaseModel):
    managed_properties: list[PropertyCandidateResponse] = Field(..., alias="managedProperties")
    imported_properties: list[PropertyCandidateResponse] = Field(..., alias="importedProperties")


class PropertyMatchRequest(BaseModel):
    source_property_id: str = Field(..., alias="sourcePropertyId")
    target_property_id: str = Field(..., alias="targetPropertyId")


class PropertyMatchResult(BaseModel):
    target_property_id: str = Field(..., alias="targetPropertyId")
    deleted_property_id: str = Field(..., alias="deletedPropertyId")
    reservations_updated: int = Field(..., alias="reservationsUpdated")
    clients_updated: int = Field(..., alias="clientsUpdated")
    mapping_id: Optional[str] = Field(None, alias="mappingId")


class BatchPropertyMatchItem(BaseModel):
    source_property_id: str = Field(..., alias="sourcePropertyId")
    target_property_id: str = Field(..., alias="targetPropertyId")
    create_mapping: bool = Field(True, alias="createMapping")


class BatchPropertyMatchRequest(BaseModel):
    matches: list[BatchPropertyMatchItem]
    delete_unmatched: bool = Field(True, alias="deleteUnmatched")


class BatchPropertyMatchResult(BaseModel):
    total_matched: int = Field(..., alias="totalMatched")
    total_reservations_updated: int = Field(..., alias="totalReservationsUpdated")
    total_clients_updated: int = Field(..., alias="totalClientsUpdated")
    total_properties_deleted: int = Field(..., alias="totalPropertiesDeleted")
    mappings_created: int = Field(..., alias="mappingsCreated")


@router.get(
    "/hosts/{host_id}/property-mappings",
    response_model=list[PropertyMappingResponse],
    status_code=status.HTTP_200_OK,
)
def list_property_mappings(
    host_id: str,
    action: Optional[PropertyMappingAction] = Query(default=None),
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> list[PropertyMappingResponse]:
    repo = PropertyNameMappingsRepository(firestore_client)
    mappings = repo.list_by_host(host_id, action=action)
    return [PropertyMappingResponse.from_record(record) for record in mappings]


@router.get(
    "/hosts/{host_id}/property-candidates",
    response_model=list[PropertyCandidateResponse],
    status_code=status.HTTP_200_OK,
)
def list_property_candidates(
    host_id: str,
    imported_from: Optional[str] = Query(default="airbnb_email"),
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> list[PropertyCandidateResponse]:
    properties_repo = PropertiesRepository(firestore_client)
    candidates = properties_repo.list_imported_properties(
        host_id,
        imported_from=imported_from,
        requires_review=True,
    )
    return [
        PropertyCandidateResponse(
            propertyId=item.get("id"),
            name=item.get("name"),
            importedFrom=item.get("importedFrom"),
            requiresReview=item.get("requiresReview", False),
            createdAt=item.get("createdAt"),
            updatedAt=item.get("updatedAt"),
        )
        for item in candidates
    ]


@router.post(
    "/hosts/{host_id}/property-mappings",
    response_model=PropertyMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_property_mapping(
    host_id: str,
    payload: CreatePropertyMappingRequest,
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> PropertyMappingResponse:
    repo = PropertyNameMappingsRepository(firestore_client)
    mapping_id = repo.create_mapping(
        host_id=host_id,
        extracted_name=payload.extracted_name,
        action=payload.action,
        target_property_id=payload.target_property_id,
        notes=payload.notes,
    )
    created = repo.get_by_id(mapping_id)
    if not created:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossibile recuperare il mapping appena creato",
        )
    return PropertyMappingResponse.from_record(created)


@router.patch(
    "/hosts/{host_id}/property-mappings/{mapping_id}",
    response_model=PropertyMappingResponse,
    status_code=status.HTTP_200_OK,
)
def update_property_mapping(
    host_id: str,
    mapping_id: str,
    payload: UpdatePropertyMappingRequest,
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> PropertyMappingResponse:
    repo = PropertyNameMappingsRepository(firestore_client)
    existing = repo.get_by_id(mapping_id)
    if not existing or existing.host_id != host_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping non trovato",
        )

    repo.update_mapping(
        mapping_id,
        extracted_name=payload.extracted_name,
        action=payload.action,
        target_property_id=payload.target_property_id,
        notes=payload.notes,
    )
    updated = repo.get_by_id(mapping_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossibile recuperare il mapping aggiornato",
        )
    return PropertyMappingResponse.from_record(updated)


@router.delete(
    "/hosts/{host_id}/property-mappings/{mapping_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_property_mapping(
    host_id: str,
    mapping_id: str,
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> None:
    repo = PropertyNameMappingsRepository(firestore_client)
    existing = repo.get_by_id(mapping_id)
    if not existing or existing.host_id != host_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping non trovato",
        )
    repo.delete_mapping(mapping_id)
    return None


@router.post(
    "/hosts/{host_id}/property-mappings/resolve",
    response_model=ResolvePropertyMappingResponse,
    status_code=status.HTTP_200_OK,
)
def resolve_property_mapping(
    host_id: str,
    payload: ResolvePropertyMappingRequest,
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> ResolvePropertyMappingResponse:
    mappings_repo = PropertyNameMappingsRepository(firestore_client)
    properties_repo = PropertiesRepository(firestore_client)
    reservations_repo = ReservationsRepository(firestore_client)

    target_property = None
    if payload.action == "map":
        target_property = properties_repo.get_by_id(payload.target_property_id)  # type: ignore[arg-type]
        if not target_property or target_property.get("hostId") != host_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property di destinazione non trovata",
            )

    mapping_id = mappings_repo.create_mapping(
        host_id=host_id,
        extracted_name=payload.extracted_name,
        action=payload.action,
        target_property_id=payload.target_property_id,
        notes=payload.notes,
    )
    created = mappings_repo.get_by_id(mapping_id)
    if not created:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Impossibile recuperare il mapping appena creato",
        )

    reassigned = 0
    deleted = 0

    if payload.action == "map" and target_property:
        properties_repo.mark_reviewed(target_property["id"])

        if payload.reassign_existing or payload.delete_auto_property:
            source_properties = properties_repo.list_by_name(host_id, payload.extracted_name)
            for prop in source_properties:
                if payload.reassign_existing and prop.get("id") != target_property["id"]:
                    reassigned += reservations_repo.reassign_property(
                        host_id=host_id,
                        from_property_id=prop["id"],
                        to_property_id=target_property["id"],
                        to_property_name=target_property.get("name"),
                    )
                if payload.delete_auto_property and prop.get("id") != target_property["id"]:
                    properties_repo.delete_property(prop["id"])
                    deleted += 1

    if payload.action == "ignore" and payload.delete_auto_property:
        source_properties = properties_repo.list_by_name(host_id, payload.extracted_name)
        for prop in source_properties:
            properties_repo.delete_property(prop["id"])
            deleted += 1

    return ResolvePropertyMappingResponse(
        mapping=PropertyMappingResponse.from_record(created),
        reassignedReservations=reassigned,
        deletedProperties=deleted,
    )


@router.get(
    "/hosts/{host_id}/property-match",
    response_model=PropertyMatchResponse,
    status_code=status.HTTP_200_OK,
)
def list_property_match_data(
    host_id: str,
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> PropertyMatchResponse:
    properties_repo = PropertiesRepository(firestore_client)

    all_properties = properties_repo.list_by_host(host_id)

    managed_raw = []
    imported_raw = []
    for item in all_properties:
        imported_from = item.get("importedFrom")
        requires_review = item.get("requiresReview", imported_from == "airbnb_email")
        if imported_from == "airbnb_email" or requires_review:
            imported_raw.append(item)
        else:
            managed_raw.append(item)

    def to_candidate(item: dict) -> PropertyCandidateResponse:
        return PropertyCandidateResponse(
            propertyId=item.get("id"),
            name=item.get("name"),
            importedFrom=item.get("importedFrom"),
            requiresReview=item.get("requiresReview", False),
            createdAt=item.get("createdAt"),
            updatedAt=item.get("updatedAt"),
        )

    return PropertyMatchResponse(
        managedProperties=[to_candidate(item) for item in managed_raw],
        importedProperties=[to_candidate(item) for item in imported_raw],
    )


@router.post(
    "/hosts/{host_id}/property-match",
    response_model=PropertyMatchResult,
    status_code=status.HTTP_200_OK,
)
def match_properties(
    host_id: str,
    payload: PropertyMatchRequest,
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> PropertyMatchResult:
    properties_repo = PropertiesRepository(firestore_client)
    reservations_repo = ReservationsRepository(firestore_client)
    clients_repo = ClientsRepository(firestore_client)
    mappings_repo = PropertyNameMappingsRepository(firestore_client)

    source = properties_repo.get_by_id(payload.source_property_id)
    if not source or source.get("hostId") != host_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property sorgente non trovata",
        )

    target = properties_repo.get_by_id(payload.target_property_id)
    if not target or target.get("hostId") != host_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property destinazione non trovata",
        )

    if not source.get("requiresReview", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La property sorgente deve provenire da import Airbnb",
        )

    target_name = target.get("name")
    reservations_updated = reservations_repo.reassign_property(
        host_id=host_id,
        from_property_id=source["id"],
        to_property_id=target["id"],
        to_property_name=target_name,
    )
    clients_updated = clients_repo.reassign_property(
        host_id=host_id,
        from_property_id=source["id"],
        to_property_id=target["id"],
    )

    # NON creiamo più mapping automatici - l'utente può fare il matching manualmente quando necessario

    properties_repo.delete_property(source["id"])

    return PropertyMatchResult(
        targetPropertyId=target["id"],
        deletedPropertyId=source["id"],
        reservationsUpdated=reservations_updated,
        clientsUpdated=clients_updated,
        mappingId=None,  # Non creiamo più mapping automatici
    )


@router.post(
    "/hosts/{host_id}/property-match/batch",
    response_model=BatchPropertyMatchResult,
    status_code=status.HTTP_200_OK,
)
def batch_match_properties(
    host_id: str,
    payload: BatchPropertyMatchRequest,
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> BatchPropertyMatchResult:
    properties_repo = PropertiesRepository(firestore_client)
    reservations_repo = ReservationsRepository(firestore_client)
    clients_repo = ClientsRepository(firestore_client)
    mappings_repo = PropertyNameMappingsRepository(firestore_client)

    total_reservations = 0
    total_clients = 0
    total_deleted = 0
    total_mappings = 0
    matched_source_ids = set()

    # Processa tutti i match richiesti
    for match_item in payload.matches:
        source = properties_repo.get_by_id(match_item.source_property_id)
        if not source or source.get("hostId") != host_id:
            continue

        target = properties_repo.get_by_id(match_item.target_property_id)
        if not target or target.get("hostId") != host_id:
            continue

        if not source.get("requiresReview", False):
            continue

        target_name = target.get("name")
        reservations_count = reservations_repo.reassign_property(
            host_id=host_id,
            from_property_id=source["id"],
            to_property_id=target["id"],
            to_property_name=target_name,
        )
        clients_count = clients_repo.reassign_property(
            host_id=host_id,
            from_property_id=source["id"],
            to_property_id=target["id"],
        )
        total_reservations += reservations_count
        total_clients += clients_count

        # Crea mapping se richiesto (per evitare duplicati in futuro)
        extracted_name = source.get("name")
        if match_item.create_mapping and extracted_name:
            mappings_repo.create_mapping(
                host_id=host_id,
                extracted_name=extracted_name,
                action="map",
                target_property_id=target["id"],
            )
            total_mappings += 1

        # Elimina la property importata
        properties_repo.delete_property(source["id"])
        total_deleted += 1
        matched_source_ids.add(source["id"])

    # Elimina le property importate non associate se richiesto
    if payload.delete_unmatched:
        all_imported = properties_repo.list_imported_properties(
            host_id, imported_from="airbnb_email", requires_review=True
        )
        for imported_prop in all_imported:
            imported_id = imported_prop.get("id")
            if imported_id not in matched_source_ids:
                # Prima elimina le prenotazioni e clienti associati a questa property
                reservations_repo.delete_by_property(host_id, imported_id)
                clients_repo.delete_by_property(host_id, imported_id)
                
                # Poi elimina la property
                properties_repo.delete_property(imported_id)
                total_deleted += 1

    return BatchPropertyMatchResult(
        totalMatched=len(matched_source_ids),
        totalReservationsUpdated=total_reservations,
        totalClientsUpdated=total_clients,
        totalPropertiesDeleted=total_deleted,
        mappingsCreated=total_mappings,
    )

