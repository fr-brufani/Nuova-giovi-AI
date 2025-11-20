from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from firebase_admin import firestore
from pydantic import BaseModel, Field

from email_agent_service.dependencies.firebase import get_firestore_client
from email_agent_service.repositories.properties import PropertiesRepository
from email_agent_service.repositories.reservations import ReservationsRepository
from email_agent_service.services.test_conversation_service import TestConversationService

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateTestReservationRequest(BaseModel):
    hostId: str = Field(..., alias="hostId")
    propertyId: str = Field(..., alias="propertyId")
    clientName: str = Field(..., alias="clientName", min_length=1)
    testHostId: str = Field(..., alias="testHostId")  # ID dell'utente test loggato
    startDate: Optional[datetime] = Field(None, alias="startDate")
    endDate: Optional[datetime] = Field(None, alias="endDate")


class CreateTestReservationResponse(BaseModel):
    reservationId: str = Field(..., alias="reservationId")
    clientId: str = Field(..., alias="clientId")
    propertyName: str = Field(..., alias="propertyName")
    propertyId: str = Field(..., alias="propertyId")
    reservationDocId: Optional[str] = Field(None, alias="reservationDocId")


class AttachmentModel(BaseModel):
    url: str
    fileName: str = Field(..., alias="fileName")
    fileType: str = Field(..., alias="fileType")


class SendTestMessageRequest(BaseModel):
    message: str = Field(..., min_length=1)
    attachments: Optional[list[AttachmentModel]] = None


class SendTestMessageResponse(BaseModel):
    messageId: str = Field(..., alias="messageId")
    aiReply: Optional[str] = Field(None, alias="aiReply")
    timestamp: datetime


class MessageResponse(BaseModel):
    id: str
    sender: str
    text: str
    timestamp: Optional[datetime]
    attachments: list[dict] = Field(default_factory=list)
    imageUrl: Optional[str] = Field(None, alias="imageUrl")
    isTest: bool = Field(..., alias="isTest")


class ConversationMessagesResponse(BaseModel):
    messages: list[MessageResponse]


class TestReservationSummary(BaseModel):
    id: str
    reservationId: Optional[str] = None
    clientId: Optional[str] = None
    clientName: Optional[str] = None
    propertyId: Optional[str] = None
    propertyName: Optional[str] = None
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    status: Optional[str] = None
    createdAt: Optional[datetime] = None
    lastUpdatedAt: Optional[datetime] = None


class TestReservationsResponse(BaseModel):
    reservations: list[TestReservationSummary]


@router.post(
    "/reservations",
    response_model=CreateTestReservationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_test_reservation(
    payload: CreateTestReservationRequest,
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> CreateTestReservationResponse:
    """Crea una reservation di test e il client associato."""
    try:
        service = TestConversationService(firestore_client)
        
        # Verifica che la property esista
        properties_repo = PropertiesRepository(firestore_client)
        property_data = properties_repo.get_by_id(payload.propertyId)
        
        if not property_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property {payload.propertyId} non trovata",
            )
        
        if property_data.get("hostId") != payload.hostId:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Property {payload.propertyId} non appartiene all'host {payload.hostId}",
            )
        
        reservation_id, client_id, reservation_doc_id = service.create_test_reservation(
            host_id=payload.hostId,
            property_id=payload.propertyId,
            client_name=payload.clientName,
            test_host_id=payload.testHostId,
            start_date=payload.startDate,
            end_date=payload.endDate,
        )
        
        return CreateTestReservationResponse(
            reservationId=reservation_id,
            clientId=client_id,
            propertyName=property_data.get("name", "Unknown Property"),
            propertyId=payload.propertyId,
            reservationDocId=reservation_doc_id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TEST] Errore creazione reservation test: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore creazione reservation test: {str(e)}",
        )


@router.post(
    "/conversations/{property_id}/{client_id}/messages",
    response_model=SendTestMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_test_message(
    property_id: str,
    client_id: str,
    payload: SendTestMessageRequest,
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> SendTestMessageResponse:
    """Invia un messaggio test e genera risposta AI."""
    try:
        service = TestConversationService(firestore_client)
        
        # Recupera reservation per questo client
        reservations_repo = ReservationsRepository(firestore_client)
        reservations_ref = firestore_client.collection("reservations")
        query = (
            reservations_ref
            .where("clientId", "==", client_id)
            .where("propertyId", "==", property_id)
            .where("isTest", "==", True)
            .limit(1)
        )
        docs = list(query.get())
        
        if not docs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reservation test non trovata per client {client_id} e property {property_id}",
            )
        
        reservation = docs[0].to_dict()
        reservation_id = reservation.get("reservationId")
        host_id = reservation.get("hostId")
        
        if not reservation_id or not host_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reservation test non valida (mancano reservationId o hostId)",
            )
        
        # Converti attachments
        attachments = None
        if payload.attachments:
            attachments = [
                {
                    "url": att.url,
                    "fileName": att.fileName,
                    "fileType": att.fileType,
                }
                for att in payload.attachments
            ]
        
        # Invia messaggio e genera risposta
        message_id, ai_reply = service.send_test_message(
            host_id=host_id,
            property_id=property_id,
            client_id=client_id,
            reservation_id=reservation_id,
            message_text=payload.message,
            attachments=attachments,
        )
        
        return SendTestMessageResponse(
            messageId=message_id,
            aiReply=ai_reply,
            timestamp=datetime.now(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TEST] Errore invio messaggio test: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore invio messaggio test: {str(e)}",
        )


@router.get(
    "/conversations/{property_id}/{client_id}/messages",
    response_model=ConversationMessagesResponse,
    status_code=status.HTTP_200_OK,
)
def get_conversation_messages(
    property_id: str,
    client_id: str,
    limit: int = 50,
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> ConversationMessagesResponse:
    """Recupera messaggi della conversazione test."""
    try:
        service = TestConversationService(firestore_client)
        
        messages = service.get_conversation_messages(
            property_id=property_id,
            client_id=client_id,
            limit=limit,
        )
        
        message_responses = [
            MessageResponse(
                id=msg["id"],
                sender=msg["sender"],
                text=msg["text"],
                timestamp=msg.get("timestamp"),
                attachments=msg.get("attachments", []),
                imageUrl=msg.get("imageUrl"),
                isTest=msg.get("isTest", False),
            )
            for msg in messages
        ]
        
        return ConversationMessagesResponse(messages=message_responses)
        
    except Exception as e:
        logger.error(f"[TEST] Errore recupero messaggi: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore recupero messaggi: {str(e)}",
        )


@router.get(
    "/test-hosts/{test_host_id}/reservations",
    response_model=TestReservationsResponse,
    status_code=status.HTTP_200_OK,
)
def list_test_reservations(
    test_host_id: str,
    property_id: Optional[str] = Query(None, alias="propertyId"),
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> TestReservationsResponse:
    """
    Restituisce le reservation di test per un utente test loggato (filtrate opzionalmente per property).
    Usa testHostId invece di hostId per filtrare le reservations.
    """
    try:
        service = TestConversationService(firestore_client)
        reservations = service.list_test_reservations_by_test_host(
            test_host_id=test_host_id,
            property_id=property_id,
        )
        return TestReservationsResponse(reservations=reservations)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TEST] Errore recupero reservations test: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore recupero reservations test: {str(e)}",
        )

