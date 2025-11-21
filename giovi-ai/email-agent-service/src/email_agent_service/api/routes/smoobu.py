"""API routes per integrazione Smoobu."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from firebase_admin import firestore
from pydantic import BaseModel, Field

from ...dependencies.firebase import get_firestore_client
from ...services.persistence_service import PersistenceService
from ...services.integrations.smoobu_client import (
    SmoobuClient,
    SmoobuAuthenticationError,
    SmoobuAPIError,
)
from ...models.smoobu_reservation import SmoobuReservation
from ...repositories.smoobu_property_mappings import SmoobuPropertyMappingsRepository
from ...repositories.properties import PropertiesRepository
from ...repositories.reservations import ReservationsRepository
from ...repositories.clients import ClientsRepository

logger = logging.getLogger(__name__)

router = APIRouter()

# Collection per salvare le API key e smoobuUserId degli host
HOST_API_KEYS_COLLECTION = "smoobuHostApiKeys"


class SmoobuImportRequest(BaseModel):
    """Request per import massivo Smoobu."""
    host_id: str = Field(..., alias="hostId")
    api_key: str = Field(..., alias="apiKey")
    from_date: Optional[str] = Field(None, alias="fromDate", description="Data inizio import (YYYY-MM-DD)")
    to_date: Optional[str] = Field(None, alias="toDate", description="Data fine import (YYYY-MM-DD)")


class SmoobuTestRequest(BaseModel):
    """Request per test connessione Smoobu."""
    api_key: str = Field(..., alias="apiKey")


class SmoobuWebhookPayload(BaseModel):
    """Payload webhook da Smoobu."""
    action: str  # newReservation, updateReservation, cancelReservation, deleteReservation
    user: int  # smoobuUserId
    data: Dict[str, Any]  # Dati prenotazione


class SmoobuImportResponse(BaseModel):
    """Response per import massivo Smoobu."""
    success: bool
    total_processed: int = Field(..., alias="totalProcessed")
    total_saved: int = Field(..., alias="totalSaved")
    total_skipped: int = Field(..., alias="totalSkipped")
    total_errors: int = Field(..., alias="totalErrors")
    properties_imported: int = Field(..., alias="propertiesImported")
    clients_imported: int = Field(..., alias="clientsImported")
    apartments: list = Field(default_factory=list)
    smoobu_user_id: Optional[int] = Field(None, alias="smoobuUserId")
    webhook_url: Optional[str] = Field(None, alias="webhookUrl")
    error: Optional[str] = None


class SmoobuTestResponse(BaseModel):
    """Response per test connessione Smoobu."""
    success: bool
    user_id: Optional[int] = Field(None, alias="userId")
    user_name: Optional[str] = Field(None, alias="userName")
    user_email: Optional[str] = Field(None, alias="userEmail")
    error: Optional[str] = None


class SmoobuStatusResponse(BaseModel):
    """Response per status integrazione Smoobu."""
    configured: bool
    smoobu_user_id: Optional[int] = Field(None, alias="smoobuUserId")
    webhook_url: Optional[str] = Field(None, alias="webhookUrl")
    last_sync: Optional[str] = Field(None, alias="lastSync")


def get_persistence_service(
    firestore_client=Depends(get_firestore_client),
) -> PersistenceService:
    """Dependency per PersistenceService."""
    return PersistenceService(firestore_client)


def get_host_id_from_smoobu_user_id(
    smoobu_user_id: int,
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> Optional[str]:
    """
    Recupera l'hostId interno basato sullo smoobuUserId.
    
    Args:
        smoobu_user_id: ID utente Smoobu
        firestore_client: Client Firestore
        
    Returns:
        host_id se trovato, None altrimenti
    """
    try:
        query = (
            firestore_client.collection(HOST_API_KEYS_COLLECTION)
            .where("smoobuUserId", "==", smoobu_user_id)
            .limit(1)
        )
        docs = list(query.get())
        
        if docs:
            host_id = docs[0].id
            logger.info(f"[SmoobuWebhook] Trovato hostId: {host_id} per smoobuUserId: {smoobu_user_id}")
            return host_id
        else:
            logger.warning(f"[SmoobuWebhook] Host NON TROVATO per smoobuUserId: {smoobu_user_id}")
            return None
    except Exception as e:
        logger.error(f"[SmoobuWebhook] Errore ricerca host per smoobuUserId {smoobu_user_id}: {e}")
        return None


def save_host_api_key(
    host_id: str,
    api_key: str,
    smoobu_user_id: int,
    firestore_client: firestore.Client,
) -> None:
    """
    Salva API key e smoobuUserId per un host.
    
    Args:
        host_id: ID host
        api_key: API key Smoobu
        smoobu_user_id: ID utente Smoobu
        firestore_client: Client Firestore
    """
    doc_ref = firestore_client.collection(HOST_API_KEYS_COLLECTION).document(host_id)
    doc_ref.set({
        "apiKey": api_key,
        "smoobuUserId": smoobu_user_id,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }, merge=True)
    logger.info(f"[SmoobuAPI] API key e smoobuUserId salvati per host {host_id}")


def import_all_reservations(
    host_id: str,
    api_key: str,
    persistence_service: PersistenceService,
    firestore_client: firestore.Client,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Import massivo iniziale di tutte le prenotazioni per un host.
    
    Args:
        host_id: ID host
        api_key: API key Smoobu
        persistence_service: Service per persistenza
        firestore_client: Client Firestore
        from_date: Data inizio import
        to_date: Data fine import
        
    Returns:
        dict con statistiche import
    """
    logger.info(f"[SmoobuAPI] 🚀 Import massivo prenotazioni per host {host_id}")
    
    if not from_date:
        from_date = datetime.now() - timedelta(days=180)  # 6 mesi
    if not to_date:
        to_date = datetime.now() + timedelta(days=365)  # 1 anno nel futuro
    
    stats = {
        "total_processed": 0,
        "total_saved": 0,
        "total_skipped": 0,
        "total_errors": 0,
        "properties_imported": 0,
        "clients_imported": 0,
        "apartments": [],
    }
    
    try:
        client = SmoobuClient(api_key=api_key, mock_mode=False)
        mappings_repo = SmoobuPropertyMappingsRepository(firestore_client)
        properties_repo = PropertiesRepository(firestore_client)
        
        # 1. Recupera e salva tutte le properties
        logger.info(f"[SmoobuAPI] Recupero apartments per host {host_id}")
        apartments_data = client.get_apartments()
        
        for apt_data in apartments_data:
            try:
                apartment = client.parse_apartment(apt_data)
                
                # Cerca mapping esistente
                existing_mapping = mappings_repo.get_by_smoobu_apartment_id(str(apartment.id))
                
                resolved_property_id = None
                property_created = False
                
                if existing_mapping and existing_mapping.internal_property_id:
                    # Usa property esistente
                    existing_property = properties_repo.get_by_id(existing_mapping.internal_property_id)
                    if existing_property:
                        resolved_property_id = existing_mapping.internal_property_id
                        logger.info(f"[SmoobuAPI] Property esistente per apartment {apartment.id}: {resolved_property_id}")
                
                if not resolved_property_id:
                    # Cerca o crea property
                    property_name = apartment.name or f"Smoobu Apartment {apartment.id}"
                    resolved_property_id, property_created = properties_repo.find_or_create_by_name(
                        host_id=host_id,
                        property_name=property_name,
                        imported_from="smoobu_api",
                    )
                    if property_created:
                        stats["properties_imported"] += 1
                        logger.info(f"[SmoobuAPI] Nuova property creata: {property_name} -> {resolved_property_id}")
                
                # Crea o aggiorna mapping
                if existing_mapping:
                    mappings_repo.update_mapping(
                        existing_mapping.id,
                        internal_property_id=resolved_property_id,
                        property_name=property_name,
                        apartment_name=apartment.name,
                    )
                else:
                    mappings_repo.create_mapping(
                        smoobu_apartment_id=str(apartment.id),
                        host_id=host_id,
                        internal_property_id=resolved_property_id,
                        property_name=property_name,
                        apartment_name=apartment.name,
                    )
                
                stats["apartments"].append({
                    "smoobu_id": apartment.id,
                    "name": apartment.name,
                    "property_id": resolved_property_id,
                })
                
            except Exception as e:
                logger.error(f"[SmoobuAPI] Errore import apartment {apt_data.get('id')}: {e}", exc_info=True)
                stats["total_errors"] += 1
        
        logger.info(f"[SmoobuAPI] Importate {len(stats['apartments'])} apartments")
        
        # 2. Recupera tutte le prenotazioni nel range
        from_str = from_date.strftime("%Y-%m-%d")
        to_str = to_date.strftime("%Y-%m-%d")
        
        logger.info(f"[SmoobuAPI] Recupero prenotazioni dal {from_str} al {to_str}")
        
        page = 1
        while True:
            response = client.get_reservations(
                from_date=from_str,
                to_date=to_str,
                page=page,
                page_size=100,
                exclude_blocked=True,
            )
            
            bookings = response.get("bookings", [])
            if not bookings:
                break
            
            logger.info(
                f"[SmoobuAPI] Processando pagina {page}/{response.get('page_count', 1)} "
                f"({len(bookings)} prenotazioni)"
            )
            
            for booking_data in bookings:
                try:
                    reservation = client.parse_reservation(booking_data)
                    
                    # Salva prenotazione (upsert gestisce già deduplica)
                    save_result = persistence_service.save_smoobu_reservation(
                        reservation=reservation,
                        host_id=host_id,
                    )
                    
                    stats["total_processed"] += 1
                    
                    if save_result.get("saved"):
                        stats["total_saved"] += 1
                        if save_result.get("client_created"):
                            stats["clients_imported"] += 1
                    elif save_result.get("skipped"):
                        stats["total_skipped"] += 1
                    else:
                        stats["total_errors"] += 1
                        logger.warning(
                            f"[SmoobuAPI] Errore salvataggio prenotazione {reservation.id}: "
                            f"{save_result.get('error', 'unknown')}"
                        )
                    
                except Exception as e:
                    logger.error(
                        f"[SmoobuAPI] Errore processando prenotazione: {e}",
                        exc_info=True,
                    )
                    stats["total_errors"] += 1
            
            # Controlla se ci sono altre pagine
            page_count = response.get("page_count", 1)
            if page >= page_count:
                break
            page += 1
        
        logger.info(
            f"[SmoobuAPI] ✅ Import massivo completato per host {host_id}: "
            f"Processate={stats['total_processed']}, Salvate={stats['total_saved']}, "
            f"Saltate={stats['total_skipped']}, Errori={stats['total_errors']}"
        )
        
    except Exception as e:
        logger.error(f"[SmoobuAPI] Errore durante import massivo: {e}", exc_info=True)
        stats["error"] = str(e)
    
    return stats


@router.post(
    "/smoobu/webhook",
    status_code=status.HTTP_200_OK,
)
async def smoobu_webhook(
    payload: SmoobuWebhookPayload = Body(...),
    persistence_service: PersistenceService = Depends(get_persistence_service),
    firestore_client=Depends(get_firestore_client),
) -> Dict[str, Any]:
    """
    Endpoint webhook per ricevere eventi da Smoobu.
    
    Gestisce:
    - newReservation: Crea nuova prenotazione
    - updateReservation: Aggiorna prenotazione esistente
    - cancelReservation: Cancella prenotazione
    - deleteReservation: Elimina prenotazione
    """
    action = payload.action
    smoobu_user_id = payload.user
    reservation_data = payload.data
    
    # Validazione payload
    if not action or not isinstance(smoobu_user_id, int) or not reservation_data or not isinstance(reservation_data.get("id"), int):
        logger.error(f"[SmoobuWebhook] Payload invalido: action={action}, user={smoobu_user_id}, data.id={reservation_data.get('id')}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload structure. Required: action, user (int), data.id (int)"
        )
    
    logger.info(
        f"[SmoobuWebhook] Ricevuta azione '{action}' per smoobuUser {smoobu_user_id}, "
        f"prenotazione Smoobu ID {reservation_data.get('id')}"
    )
    
    # Recupera host_id da smoobuUserId
    host_id = get_host_id_from_smoobu_user_id(smoobu_user_id, firestore_client)
    if not host_id:
        logger.warning(f"[SmoobuWebhook] Host non trovato per smoobuUserId {smoobu_user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Host configuration not found for Smoobu user ID {smoobu_user_id}. Please configure Smoobu integration."
        )
    
    try:
        # Parse reservation data
        client = SmoobuClient(api_key="", mock_mode=False)  # Non serve API key per parsing
        reservation = client.parse_reservation(reservation_data)
        
        # Gestisci azioni
        action_lower = action.lower()
        
        if action_lower == "newreservation":
            save_result = persistence_service.save_smoobu_reservation(
                reservation=reservation,
                host_id=host_id,
            )
            if save_result.get("saved"):
                logger.info(f"[SmoobuWebhook] ✅ Nuova prenotazione {reservation.id} salvata per host {host_id}")
                return {"success": True, "message": f"New reservation {reservation.id} processed", "action": "new"}
            else:
                logger.warning(f"[SmoobuWebhook] ⚠️ Prenotazione {reservation.id} non salvata: {save_result.get('error')}")
                return {"success": False, "message": f"Reservation not saved: {save_result.get('error')}", "action": "new"}
        
        elif action_lower == "updatereservation":
            save_result = persistence_service.update_smoobu_reservation(
                reservation=reservation,
                host_id=host_id,
            )
            if save_result.get("saved") or save_result.get("skipped"):
                logger.info(f"[SmoobuWebhook] ✅ Prenotazione {reservation.id} aggiornata per host {host_id}")
                return {"success": True, "message": f"Reservation {reservation.id} updated", "action": "update"}
            else:
                logger.warning(f"[SmoobuWebhook] ⚠️ Prenotazione {reservation.id} non aggiornata: {save_result.get('error')}")
                return {"success": False, "message": f"Reservation not updated: {save_result.get('error')}", "action": "update"}
        
        elif action_lower == "cancelreservation":
            save_result = persistence_service.cancel_smoobu_reservation(
                reservation_id=str(reservation.id),
                host_id=host_id,
            )
            if save_result.get("cancelled") or save_result.get("saved"):
                logger.info(f"[SmoobuWebhook] ✅ Prenotazione {reservation.id} cancellata per host {host_id}")
                return {"success": True, "message": f"Reservation {reservation.id} cancelled", "action": "cancel"}
            else:
                logger.warning(f"[SmoobuWebhook] ⚠️ Prenotazione {reservation.id} non cancellata: {save_result.get('error')}")
                return {"success": False, "message": f"Reservation not cancelled: {save_result.get('error')}", "action": "cancel"}
        
        elif action_lower == "deletereservation":
            # Elimina completamente la prenotazione
            try:
                from ...repositories.reservations import ReservationsRepository
                reservations_repo = ReservationsRepository(firestore_client)
                deleted = reservations_repo.delete_by_reservation_id(
                    reservation_id=str(reservation.id),
                    host_id=host_id,
                )
                if deleted:
                    logger.info(f"[SmoobuWebhook] ✅ Prenotazione {reservation.id} eliminata per host {host_id}")
                    return {"success": True, "message": f"Reservation {reservation.id} deleted", "action": "delete"}
                else:
                    logger.warning(f"[SmoobuWebhook] ⚠️ Prenotazione {reservation.id} non trovata per eliminazione")
                    return {"success": True, "message": f"Reservation {reservation.id} not found (already deleted)", "action": "delete"}
            except Exception as e:
                logger.error(f"[SmoobuWebhook] Errore eliminazione prenotazione {reservation.id}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error deleting reservation: {str(e)}"
                )
        
        else:
            logger.warning(f"[SmoobuWebhook] Azione non gestita: {action}")
            return {"success": True, "message": f"Action '{action}' received but not handled", "action": action}
    
    except Exception as e:
        logger.error(
            f"[SmoobuWebhook] Errore critico processando webhook (Azione: {action}, Smoobu ID: {reservation_data.get('id')}): {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error while processing webhook: {str(e)}"
        )


@router.post(
    "/smoobu/import",
    response_model=SmoobuImportResponse,
    status_code=status.HTTP_200_OK,
)
def import_smoobu_reservations(
    request: SmoobuImportRequest,
    persistence_service: PersistenceService = Depends(get_persistence_service),
    firestore_client=Depends(get_firestore_client),
) -> SmoobuImportResponse:
    """
    Import massivo iniziale di prenotazioni Smoobu.
    
    - Valida API key
    - Recupera smoobuUserId
    - Importa tutte le properties
    - Importa tutte le prenotazioni nel range specificato
    - Salva API key e smoobuUserId per webhook
    """
    try:
        # 1. Valida API key e recupera user info
        logger.info(f"[SmoobuAPI] Test connessione per host {request.host_id}")
        client = SmoobuClient(api_key=request.api_key, mock_mode=False)
        
        try:
            user_info = client.get_user()
            smoobu_user_id = user_info.get("id")
            if not smoobu_user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="API key valida ma user ID non trovato nella risposta"
                )
            # Assicurati che smoobu_user_id sia un int
            if not isinstance(smoobu_user_id, int):
                try:
                    smoobu_user_id = int(smoobu_user_id)
                except (ValueError, TypeError):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"User ID non valido: {smoobu_user_id}"
                    )
            logger.info(f"[SmoobuAPI] ✅ API key valida per user {smoobu_user_id}")
        except SmoobuAuthenticationError as e:
            logger.error(f"[SmoobuAPI] ❌ API key non valida: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"API key non valida: {str(e)}"
            )
        
        # 2. Parse date
        from_date = None
        to_date = None
        
        if request.from_date:
            try:
                from_date = datetime.strptime(request.from_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="fromDate deve essere in formato YYYY-MM-DD"
                )
        
        if request.to_date:
            try:
                to_date = datetime.strptime(request.to_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="toDate deve essere in formato YYYY-MM-DD"
                )
        
        # 3. Salva API key e smoobuUserId
        save_host_api_key(
            host_id=request.host_id,
            api_key=request.api_key,
            smoobu_user_id=smoobu_user_id,
            firestore_client=firestore_client,
        )
        
        # 4. Esegui import massivo
        logger.info(f"[SmoobuAPI] 🚀 Avvio import massivo per host {request.host_id}")
        stats = import_all_reservations(
            host_id=request.host_id,
            api_key=request.api_key,
            persistence_service=persistence_service,
            firestore_client=firestore_client,
            from_date=from_date,
            to_date=to_date,
        )
        
        # 5. Genera URL webhook (da configurare in Smoobu)
        # In produzione, questo dovrebbe essere l'URL pubblico del servizio
        import os
        webhook_base_url = os.getenv("WEBHOOK_BASE_URL", "https://your-service-url.com")
        webhook_url = f"{webhook_base_url}/integrations/smoobu/webhook"
        
        return SmoobuImportResponse(
            success=True,
            totalProcessed=stats.get("total_processed", 0),
            totalSaved=stats.get("total_saved", 0),
            totalSkipped=stats.get("total_skipped", 0),
            totalErrors=stats.get("total_errors", 0),
            propertiesImported=stats.get("properties_imported", 0),
            clientsImported=stats.get("clients_imported", 0),
            apartments=stats.get("apartments", []),
            smoobuUserId=smoobu_user_id,
            webhookUrl=webhook_url,
            error=stats.get("error"),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SmoobuAPI] Errore durante import: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore durante import: {str(e)}"
        )


@router.post(
    "/smoobu/test",
    response_model=SmoobuTestResponse,
    status_code=status.HTTP_200_OK,
)
def test_smoobu_connection(
    request: SmoobuTestRequest,
) -> SmoobuTestResponse:
    """
    Test connessione API Smoobu senza importare dati.
    
    Valida solo l'API key e restituisce informazioni utente.
    """
    try:
        client = SmoobuClient(api_key=request.api_key, mock_mode=False)
        user_info = client.get_user()
        
        return SmoobuTestResponse(
            success=True,
            userId=user_info.get("id"),
            userName=f"{user_info.get('firstName', '')} {user_info.get('lastName', '')}".strip(),
            userEmail=user_info.get("email"),
        )
        
    except SmoobuAuthenticationError as e:
        return SmoobuTestResponse(
            success=False,
            error=f"API key non valida: {str(e)}"
        )
    except Exception as e:
        logger.error(f"[SmoobuAPI] Errore test connessione: {e}", exc_info=True)
        return SmoobuTestResponse(
            success=False,
            error=f"Errore connessione: {str(e)}"
        )


@router.get(
    "/smoobu/status",
    response_model=SmoobuStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_smoobu_status(
    host_id: str = Query(..., alias="hostId"),
    firestore_client=Depends(get_firestore_client),
) -> SmoobuStatusResponse:
    """
    Recupera stato integrazione Smoobu per un host.
    """
    try:
        # Verifica se c'è API key configurata
        doc_ref = firestore_client.collection(HOST_API_KEYS_COLLECTION).document(host_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return SmoobuStatusResponse(
                configured=False,
                smoobu_user_id=None,
                webhook_url=None,
                last_sync=None,
            )
        
        data = doc.to_dict() or {}
        smoobu_user_id = data.get("smoobuUserId")
        
        # Genera URL webhook
        import os
        webhook_base_url = os.getenv("WEBHOOK_BASE_URL", "https://your-service-url.com")
        webhook_url = f"{webhook_base_url}/integrations/smoobu/webhook"
        
        # Recupera last sync da timestamp
        last_sync = None
        if data.get("updatedAt"):
            updated_at = data.get("updatedAt")
            if hasattr(updated_at, "timestamp"):
                last_sync = datetime.fromtimestamp(updated_at.timestamp()).isoformat()
        
        return SmoobuStatusResponse(
            configured=True,
            smoobu_user_id=smoobu_user_id,
            webhook_url=webhook_url,
            last_sync=last_sync,
        )
        
    except Exception as e:
        logger.error(f"[SmoobuAPI] Errore recupero status: {e}", exc_info=True)
        return SmoobuStatusResponse(
            configured=False,
            smoobu_user_id=None,
            webhook_url=None,
            last_sync=None,
        )


@router.delete(
    "/smoobu",
    status_code=status.HTTP_200_OK,
)
def remove_smoobu_integration(
    host_id: str = Query(..., alias="hostId"),
    firestore_client=Depends(get_firestore_client),
) -> dict:
    """
    Rimuove integrazione Smoobu per un host.
    
    Elimina:
    - API key e smoobuUserId
    - Tutte le prenotazioni con importedFrom="smoobu_api"
    - Tutti i clienti con importedFrom="smoobu_api"
    - Tutte le properties con importedFrom="smoobu_api"
    - Tutti i mapping Smoobu property
    """
    try:
        # Inizializza repository
        reservations_repo = ReservationsRepository(firestore_client)
        clients_repo = ClientsRepository(firestore_client)
        properties_repo = PropertiesRepository(firestore_client)
        mappings_repo = SmoobuPropertyMappingsRepository(firestore_client)
        
        imported_from = "smoobu_api"
        
        # Elimina prenotazioni, clienti e properties importate da Smoobu
        reservations_deleted = reservations_repo.delete_by_imported_from(host_id, imported_from)
        clients_deleted = clients_repo.delete_by_imported_from(host_id, imported_from)
        properties_deleted = properties_repo.delete_by_imported_from(host_id, imported_from)
        
        # Elimina mapping Smoobu per questo host
        mappings = mappings_repo.get_by_host(host_id)
        mappings_deleted = 0
        for mapping in mappings:
            mappings_repo.delete_mapping(mapping.id)
            mappings_deleted += 1
        
        # Rimuovi API key e smoobuUserId
        doc_ref = firestore_client.collection(HOST_API_KEYS_COLLECTION).document(host_id)
        doc_ref.delete()
        
        logger.info(
            f"[SmoobuAPI] Integrazione Smoobu rimossa per host {host_id}: "
            f"{reservations_deleted} prenotazioni, {clients_deleted} clienti, "
            f"{properties_deleted} properties, {mappings_deleted} mapping eliminati"
        )
        
        return {
            "success": True,
            "message": "Integrazione Smoobu rimossa",
            "deleted": {
                "reservations": reservations_deleted,
                "clients": clients_deleted,
                "properties": properties_deleted,
                "mappings": mappings_deleted,
            }
        }
    except Exception as e:
        logger.error(f"[SmoobuAPI] Errore rimozione integrazione: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore durante rimozione: {str(e)}"
        )
