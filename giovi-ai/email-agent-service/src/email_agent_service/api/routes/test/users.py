from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from firebase_admin import firestore
from pydantic import BaseModel, EmailStr, Field

from email_agent_service.dependencies.firebase import get_firestore_client

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateTestUserRequest(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=6)


class CreateTestUserResponse(BaseModel):
    userId: str = Field(..., alias="userId")
    email: str
    name: str
    isTest: bool = Field(True, alias="isTest")


@router.post(
    "/users",
    response_model=CreateTestUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_test_user(
    payload: CreateTestUserRequest,
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> CreateTestUserResponse:
    """
    Crea un account utente di test.
    
    Nota: Non crea un host nel database. L'utente test serve solo come identificatore
    lato frontend per sapere che siamo in modalità test. Non viene salvato nulla nel DB.
    """
    try:
        # Genera un ID univoco per l'utente test (non salvato nel DB)
        test_user_id = str(uuid.uuid4())
        
        logger.info(f"[TEST] Utente test creato (solo frontend): {test_user_id}, email={payload.email}")
        
        # Non salva nulla nel DB, restituisce solo l'ID generato
        return CreateTestUserResponse(
            userId=test_user_id,
            email=payload.email,
            name=payload.name,
            isTest=True,
        )
    except Exception as e:
        logger.error(f"[TEST] Errore creazione utente test: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore creazione utente test: {str(e)}",
        )

