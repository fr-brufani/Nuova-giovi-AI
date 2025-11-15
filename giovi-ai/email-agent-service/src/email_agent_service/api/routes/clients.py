from fastapi import APIRouter, Depends, HTTPException, status
from firebase_admin import firestore
from pydantic import BaseModel, Field

from ...dependencies.firebase import get_firestore_client
from ...repositories import ClientsRepository

router = APIRouter()


class UpdateAutoReplyRequest(BaseModel):
    host_id: str = Field(..., alias="hostId")
    enabled: bool


class UpdateAllAutoReplyRequest(BaseModel):
    host_id: str = Field(..., alias="hostId")
    enabled: bool


@router.patch(
    "/{client_id}/auto-reply",
    status_code=status.HTTP_200_OK,
)
def update_client_auto_reply(
    client_id: str,
    payload: UpdateAutoReplyRequest,
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> dict:
    """
    Aggiorna il flag autoReplyEnabled per un cliente.
    
    Args:
        client_id: ID del cliente
        payload: Payload con hostId e enabled
    """
    # Verifica che il cliente appartenga all'host
    clients_repo = ClientsRepository(firestore_client)
    
    # Recupera il cliente
    client_doc = firestore_client.collection("clients").document(client_id).get()
    if not client_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cliente {client_id} non trovato",
        )
    
    client_data = client_doc.to_dict()
    assigned_host_id = client_data.get("assignedHostId")
    
    # Verifica che il cliente appartenga all'host specificato
    if assigned_host_id != payload.host_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cliente non appartiene all'host specificato",
        )
    
    # Aggiorna autoReplyEnabled
    client_doc.reference.update(
        {
            "autoReplyEnabled": payload.enabled,
            "lastUpdatedAt": firestore.SERVER_TIMESTAMP,
        }
    )
    
    return {
        "clientId": client_id,
        "autoReplyEnabled": payload.enabled,
        "message": "Preferenza aggiornata con successo",
    }


@router.patch(
    "/auto-reply/bulk",
    status_code=status.HTTP_200_OK,
)
def update_all_clients_auto_reply(
    payload: UpdateAllAutoReplyRequest,
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> dict:
    """
    Aggiorna il flag autoReplyEnabled per tutti i clienti di un host.
    
    Args:
        payload: Payload con hostId e enabled
    """
    # Trova tutti i clienti dell'host
    clients_query = (
        firestore_client.collection("clients")
        .where("assignedHostId", "==", payload.host_id)
        .stream()
    )
    
    updated_count = 0
    batch = firestore_client.batch()
    batch_count = 0
    max_batch_size = 500  # Limite Firestore per batch
    
    try:
        for client_doc in clients_query:
            client_ref = firestore_client.collection("clients").document(client_doc.id)
            batch.update(
                client_ref,
                {
                    "autoReplyEnabled": payload.enabled,
                    "lastUpdatedAt": firestore.SERVER_TIMESTAMP,
                }
            )
            batch_count += 1
            
            # Commit batch quando raggiunge il limite
            if batch_count >= max_batch_size:
                batch.commit()
                updated_count += batch_count
                batch = firestore_client.batch()
                batch_count = 0
        
        # Commit batch finale
        if batch_count > 0:
            batch.commit()
            updated_count += batch_count
        
        return {
            "hostId": payload.host_id,
            "autoReplyEnabled": payload.enabled,
            "updatedCount": updated_count,
            "message": f"Preferenze aggiornate per {updated_count} clienti",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore durante aggiornamento bulk: {str(e)}",
        ) from e

