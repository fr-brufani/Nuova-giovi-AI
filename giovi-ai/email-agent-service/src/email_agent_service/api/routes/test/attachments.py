from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from firebase_admin import firestore
from pydantic import BaseModel, Field

from email_agent_service.dependencies.firebase import get_firestore_client
from email_agent_service.services.test_storage_service import TestStorageService

logger = logging.getLogger(__name__)

router = APIRouter()


class UploadAttachmentResponse(BaseModel):
    url: str
    fileName: str
    fileType: str


@router.post(
    "/conversations/{property_id}/{client_id}/attachments",
    response_model=UploadAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    property_id: str,
    client_id: str,
    file: UploadFile = File(...),
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> UploadAttachmentResponse:
    """
    Upload di un allegato/immagine per una conversazione test.
    
    property_id: ID della property
    client_id: ID del client test
    """
    try:
        # Leggi file
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File vuoto",
            )
        
        # Limite dimensione (es. 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File troppo grande. Dimensione massima: {max_size / 1024 / 1024}MB",
            )
        
        # Verifica tipo file (solo immagini per ora)
        allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        file_type = file.content_type or "application/octet-stream"
        
        if file_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo file non supportato. Tipi supportati: {', '.join(allowed_types)}",
            )
        
        # Upload
        conversation_id = f"{property_id}/{client_id}"  # ID conversazione per organizzare file
        storage_service = TestStorageService(firestore_client)
        result = storage_service.upload_test_attachment(
            file_content=file_content,
            file_name=file.filename or "attachment",
            file_type=file_type,
            conversation_id=conversation_id,
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Errore durante upload file",
            )
        
        return UploadAttachmentResponse(
            url=result["url"],
            fileName=result["fileName"],
            fileType=result["fileType"],
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TEST] Errore upload allegato: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore upload allegato: {str(e)}",
        )

