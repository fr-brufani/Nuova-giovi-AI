from typing import TYPE_CHECKING

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from firebase_admin import firestore

from ...dependencies.firebase import get_firestore_client
from ...models import (
    GmailCallbackRequest,
    GmailCallbackResponse,
    GmailIntegrationStartRequest,
    GmailIntegrationStartResponse,
    GmailBackfillResponse,
    GmailBackfillPreviewResponse,
    GmailWatchRequest,
    GmailWatchResponse,
    GmailNotificationPayload,
    ScidooConfigureRequest,
    ScidooConfigureResponse,
    ScidooSyncRequest,
    ScidooSyncResponse,
    ScidooTestRequest,
    ScidooTestResponse,
    ScidooRoomType,
    ScidooRoomTypesResponse,
)
from ...parsers import (
    ScidooCancellationParser,
    AirbnbConfirmationParser,
    AirbnbCancellationParser,
    AirbnbMessageParser,
    BookingConfirmationParser,
    BookingMessageParser,
    ScidooConfirmationParser,
    EmailParsingEngine,
)
from ...repositories import (
    HostEmailIntegrationRepository,
    OAuthStateRepository,
    ScidooIntegrationsRepository,
    ScidooPropertyMappingsRepository,
    ReservationsRepository,
    ClientsRepository,
    PropertiesRepository,
)
from ...services import (
    GmailOAuthService,
    OAuthStateExpiredError,
    OAuthStateNotFoundError,
    OAuthTokenExchangeError,
)
from ...repositories.processed_messages import ProcessedMessageRepository
from ...services.backfill_service import GmailBackfillService
from ...services.gmail_service import GmailService
from ...services.gmail_watch_service import GmailWatchService
from ...services.persistence_service import PersistenceService
from ...services.integrations.scidoo_reservation_client import (
    ScidooReservationClient,
    ScidooAPIError,
    ScidooAuthenticationError,
)
from ...config.settings import get_settings
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def get_oauth_service(
    firestore_client=Depends(get_firestore_client),
) -> GmailOAuthService:
    state_repo = OAuthStateRepository(firestore_client)
    integration_repo = HostEmailIntegrationRepository(firestore_client)
    return GmailOAuthService(state_repo, integration_repo, firestore_client=firestore_client)


def get_backfill_service(
    firestore_client=Depends(get_firestore_client),
) -> GmailBackfillService:
    integration_repo = HostEmailIntegrationRepository(firestore_client)
    processed_repo = ProcessedMessageRepository(firestore_client)
    gmail_service = GmailService(integration_repo)
    persistence_service = PersistenceService(firestore_client)
    engine = EmailParsingEngine(
        [
            # IMPORTANTE: ScidooCancellationParser e ScidooConfirmationParser devono essere PRIMA
            # perché BookingConfirmationParser matcha anche @scidoo.com
            ScidooCancellationParser(),
            ScidooConfirmationParser(),
            AirbnbCancellationParser(),  # Prima di AirbnbConfirmationParser per matchare cancellazioni
            AirbnbConfirmationParser(),
            BookingConfirmationParser(),
            BookingMessageParser(),
            AirbnbMessageParser(),
        ]
    )
    return GmailBackfillService(
        gmail_service=gmail_service,
        integration_repository=integration_repo,
        processed_repository=processed_repo,
        parsing_engine=engine,
        persistence_service=persistence_service,
    )


@router.post(
    "/gmail/start",
    response_model=GmailIntegrationStartResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_gmail_integration(
    payload: GmailIntegrationStartRequest,
    service: GmailOAuthService = Depends(get_oauth_service),
    db: firestore.Client = Depends(get_firestore_client),
) -> GmailIntegrationStartResponse:
    # Pulisci gli state scaduti prima di crearne uno nuovo (mantiene il DB pulito)
    from ...repositories.oauth_states import OAuthStateRepository
    state_repo = OAuthStateRepository(db)
    deleted_count = state_repo.delete_expired_states()
    
    authorization_url, state, expires_at = service.generate_authorization_url(
        host_id=payload.host_id,
        email=payload.email,
        redirect_uri=str(payload.redirect_uri) if payload.redirect_uri else None,
    )
    return GmailIntegrationStartResponse(
        authorizationUrl=authorization_url,
        state=state,
        expiresAt=expires_at,
    )


@router.post(
    "/gmail/callback",
    response_model=GmailCallbackResponse,
    status_code=status.HTTP_200_OK,
)
def handle_gmail_callback(
    payload: GmailCallbackRequest,
    service: GmailOAuthService = Depends(get_oauth_service),
) -> GmailCallbackResponse:
    try:
        integration_record = service.handle_callback(
            state=payload.state,
            code=payload.code,
            email=payload.email,
            redirect_uri=str(payload.redirect_uri) if payload.redirect_uri else None,
        )
    except OAuthStateNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except OAuthStateExpiredError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except OAuthTokenExchangeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except Exception as exc:
        # Cattura qualsiasi altro errore (es. durante fetch_token) e restituiscilo con header CORS
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore durante il callback OAuth: {str(exc)}"
        ) from exc

    return GmailCallbackResponse(
        status=integration_record.status,
        hostId=integration_record.host_id,
        email=integration_record.email,
    )


@router.post(
    "/gmail/{email}/backfill",
    response_model=GmailBackfillResponse,
    status_code=status.HTTP_200_OK,
)
def trigger_backfill(
    email: str,
    host_id: str,
    force: bool = False,
    service: GmailBackfillService = Depends(get_backfill_service),
    firestore_client=Depends(get_firestore_client),
) -> GmailBackfillResponse:
    """
    Esegue il backfill delle email.
    
    Args:
        email: Email dell'integrazione Gmail
        host_id: ID dell'host
        force: Se True, riprocessa anche le email già processate (default: False)
    """
    parsed_results = service.run_backfill(host_id=host_id, email=email, force=force, firestore_client=firestore_client)
    return GmailBackfillResponse(processed=len(parsed_results), items=parsed_results)


@router.post(
    "/gmail/{email}/backfill/preview",
    response_model=GmailBackfillPreviewResponse,
    status_code=status.HTTP_200_OK,
)
def trigger_backfill_preview(
    email: str,
    host_id: str,
    force: bool = False,
    service: GmailBackfillService = Depends(get_backfill_service),
    firestore_client=Depends(get_firestore_client),
) -> GmailBackfillPreviewResponse:
    """
    Esegue un backfill in modalità preview (nessun dato viene salvato).
    Restituisce il riepilogo delle property e prenotazioni estratte per poterle mappare manualmente.
    """
    preview = service.run_preview(
        host_id=host_id,
        email=email,
        force=force,
        firestore_client=firestore_client,
    )
    return preview


def get_watch_service(
    firestore_client=Depends(get_firestore_client),
) -> GmailWatchService:
    integration_repo = HostEmailIntegrationRepository(firestore_client)
    processed_repo = ProcessedMessageRepository(firestore_client)
    gmail_service = GmailService(integration_repo)
    persistence_service = PersistenceService(firestore_client)
    engine = EmailParsingEngine(
        [
            ScidooCancellationParser(),
            ScidooConfirmationParser(),
            AirbnbCancellationParser(),  # Prima di AirbnbConfirmationParser per matchare cancellazioni
            AirbnbConfirmationParser(),
            BookingConfirmationParser(),
            BookingMessageParser(),
            AirbnbMessageParser(),
        ]
    )
    return GmailWatchService(
        gmail_service=gmail_service,
        integration_repository=integration_repo,
        processed_repository=processed_repo,
        parsing_engine=engine,
        persistence_service=persistence_service,
        firestore_client=firestore_client,
    )


@router.post(
    "/gmail/{email}/watch",
    response_model=GmailWatchResponse,
    status_code=status.HTTP_200_OK,
)
def setup_gmail_watch(
    email: str,
    payload: GmailWatchRequest,
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> GmailWatchResponse:
    """
    Configura Gmail Watch per ricevere notifiche real-time di nuove email.
    
    Args:
        email: Email dell'integrazione Gmail
        payload: Payload con topic_name opzionale
    """
    settings = get_settings()
    integration_repo = HostEmailIntegrationRepository(firestore_client)
    integration = integration_repo.get_by_email(email)
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integrazione Gmail non trovata per {email}",
        )

    # Usa topic_name dal payload o dalle settings
    topic_name = payload.topic_name or settings.gmail_pubsub_topic
    if not topic_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Topic Pub/Sub non configurato. Fornire topicName nel payload o configurare GMAIL_PUBSUB_TOPIC",
        )

    gmail_service = GmailService(integration_repo)
    try:
        watch_result = gmail_service.setup_watch(integration, topic_name)
        history_id = watch_result["historyId"]
        expiration_ms = watch_result["expiration"]
        
        # Converti expiration in int se necessario (Gmail API può restituire stringa)
        if isinstance(expiration_ms, str):
            expiration_ms = int(expiration_ms)
        elif not isinstance(expiration_ms, int):
            expiration_ms = int(expiration_ms)

        # Salva watch subscription in Firestore
        integration_repo.update_watch_subscription(
            email=email,
            history_id=history_id,
            expiration_ms=expiration_ms,
        )

        return GmailWatchResponse(
            historyId=history_id,
            expiration=expiration_ms,
            status="active",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore durante setup Gmail Watch: {str(e)}",
        ) from e


@router.patch(
    "/hosts/{host_id}/airbnb-only",
    status_code=status.HTTP_200_OK,
)
def toggle_airbnb_only(
    host_id: str,
    enabled: bool = Query(..., description="Attiva (true) o disattiva (false) modalità Airbnb only"),
    firestore_client=Depends(get_firestore_client),
) -> dict:
    """
    Attiva/disattiva la modalità "Airbnb only" per un host.
    
    Query parameter: enabled (bool)
    - Se enabled=True: il sistema processerà solo email Airbnb
    - Se enabled=False: il sistema processerà email Booking e Airbnb (comportamento normale)
    """
    try:
        host_doc_ref = firestore_client.collection("hosts").document(host_id)
        host_doc_ref.set(
            {"airbnbOnly": enabled},
            merge=True,
        )
        return {
            "hostId": host_id,
            "airbnbOnly": enabled,
            "message": f"Modalità Airbnb only {'attivata' if enabled else 'disattivata'}",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore aggiornamento airbnbOnly: {str(e)}",
        )


@router.patch(
    "/hosts/{host_id}/auto-reply-to-new-reservations",
    status_code=status.HTTP_200_OK,
)
def toggle_auto_reply_to_new_reservations(
    host_id: str,
    enabled: bool = Query(..., description="Attiva (true) o disattiva (false) auto-reply a messaggi in nuove prenotazioni"),
    firestore_client=Depends(get_firestore_client),
) -> dict:
    """
    Attiva/disattiva l'auto-reply per messaggi allegati a nuove prenotazioni.
    
    Query parameter: enabled (bool)
    - Se enabled=True: i messaggi contenuti nelle email di conferma prenotazione verranno processati per generare risposta AI
    - Se enabled=False: i messaggi in nuove prenotazioni non verranno processati (default)
    """
    try:
        host_doc_ref = firestore_client.collection("hosts").document(host_id)
        host_doc_ref.set(
            {"autoReplyToNewReservations": enabled},
            merge=True,
        )
        return {
            "hostId": host_id,
            "autoReplyToNewReservations": enabled,
            "message": f"Auto-reply a nuove prenotazioni {'attivato' if enabled else 'disattivato'}",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore aggiornamento autoReplyToNewReservations: {str(e)}",
        )


@router.delete(
    "/gmail/{email}",
    status_code=status.HTTP_200_OK,
)
def delete_gmail_integration(
    email: str,
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> dict:
    """
    Elimina un'integrazione Gmail.
    
    Args:
        email: Email dell'integrazione Gmail da eliminare
    """
    integration_repo = HostEmailIntegrationRepository(firestore_client)
    integration = integration_repo.get_by_email(email)
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Integrazione Gmail non trovata per {email}",
        )
    
    integration_repo.delete_integration(email)
    
    return {
        "email": email,
        "message": "Integrazione Gmail eliminata con successo",
    }


@router.post(
    "/gmail/notifications",
    status_code=status.HTTP_204_NO_CONTENT,
)
def handle_gmail_notifications(
    request_body: dict,
    background_tasks: BackgroundTasks,
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> Response:
    """
    Handler per notifiche Pub/Sub da Gmail Watch.
    
    Riceve notifiche push quando arrivano nuove email e le processa in background.
    """
    import base64
    import json
    import logging

    logger = logging.getLogger(__name__)

    # Verifica formato messaggio Pub/Sub
    if not request_body.get("message") or not request_body["message"].get("data"):
        logger.warning("Notifica Pub/Sub con formato non valido")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    try:
        # Decodifica payload base64
        message_data = request_body["message"]["data"]
        payload_string = base64.b64decode(message_data).decode("utf-8")
        notification_payload = json.loads(payload_string)

        email_address = notification_payload.get("emailAddress")
        history_id = notification_payload.get("historyId")

        if not email_address or not history_id:
            logger.warning(f"Notifica Pub/Sub senza emailAddress o historyId: {notification_payload}")
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        # Crea watch service e processa in background
        integration_repo = HostEmailIntegrationRepository(firestore_client)
        processed_repo = ProcessedMessageRepository(firestore_client)
        gmail_service = GmailService(integration_repo)
        persistence_service = PersistenceService(firestore_client)
        engine = EmailParsingEngine(
            [
                ScidooCancellationParser(),
                ScidooConfirmationParser(),
                AirbnbCancellationParser(),  # Prima di AirbnbConfirmationParser per matchare cancellazioni
                AirbnbConfirmationParser(),
                BookingConfirmationParser(),
                BookingMessageParser(),
                AirbnbMessageParser(),
            ]
        )
        watch_service = GmailWatchService(
            gmail_service=gmail_service,
            integration_repository=integration_repo,
            processed_repository=processed_repo,
            parsing_engine=engine,
            persistence_service=persistence_service,
            firestore_client=firestore_client,
        )

        # Processa in background (non bloccare la risposta)
        background_tasks.add_task(watch_service.process_new_emails, email_address, history_id)

    except Exception as e:
        logger.error(f"Errore processamento notifica Gmail: {e}", exc_info=True)

    # Rispondi immediatamente con 204 No Content (ack a Pub/Sub)
    # BackgroundTasks viene eseguito dopo la risposta
    return Response(status_code=status.HTTP_204_NO_CONTENT, background=background_tasks)


# ============================================================================
# Scidoo API Integration Endpoints
# ============================================================================


def get_scidoo_persistence_service(
    firestore_client=Depends(get_firestore_client),
) -> PersistenceService:
    """Dependency per PersistenceService."""
    return PersistenceService(firestore_client)


@router.post(
    "/scidoo/{host_id}/configure",
    response_model=ScidooConfigureResponse,
    status_code=status.HTTP_200_OK,
)
def configure_scidoo_integration(
    host_id: str,
    payload: ScidooConfigureRequest,
    firestore_client: firestore.Client = Depends(get_firestore_client),
    persistence_service: PersistenceService = Depends(get_scidoo_persistence_service),
) -> ScidooConfigureResponse:
    """
    Configura integrazione Scidoo per un host.
    
    Salva API key e opzionalmente triggera import massivo iniziale.
    """
    try:
        # Salva API key
        integrations_repo = ScidooIntegrationsRepository(firestore_client)
        integrations_repo.save_api_key(host_id, payload.api_key)
        logger.info(f"[SCIDOO] API key salvata per host {host_id}")
        
        # Test connessione
        client = ScidooReservationClient(api_key=payload.api_key, mock_mode=False)
        account_info = client.get_account_info()
        
        account_name = account_info.get("name")
        properties = account_info.get("properties", [])
        properties_count = len(properties) if isinstance(properties, list) else 0
        
        sync_triggered = False
        
        # Se trigger_sync=True, esegui import massivo
        if payload.trigger_sync:
            try:
                # Import ultimi 6 mesi basato su data di creazione prenotazione
                creation_from = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
                creation_to = datetime.now().strftime("%Y-%m-%d")
                
                reservations = client.get_reservations(
                    creation_from=creation_from,
                    creation_to=creation_to,
                )
                
                processed = 0
                skipped = 0
                errors = 0
                
                for reservation in reservations:
                    try:
                        save_result = persistence_service.save_scidoo_reservation(reservation, host_id)
                        if save_result.get("saved"):
                            processed += 1
                        elif save_result.get("skipped"):
                            skipped += 1
                        else:
                            errors += 1
                    except Exception as e:
                        errors += 1
                        logger.error(f"Errore salvataggio prenotazione {reservation.internal_id}: {e}")
                
                sync_triggered = True
                logger.info(
                    f"[SCIDOO] Import massivo completato per host {host_id}: "
                    f"{processed} processate, {skipped} saltate, {errors} errori"
                )
            except Exception as e:
                logger.error(f"Errore durante import massivo Scidoo: {e}", exc_info=True)
        
        return ScidooConfigureResponse(
            hostId=host_id,
            connected=True,
            accountName=account_name,
            propertiesCount=properties_count,
            syncTriggered=sync_triggered,
        )
        
    except ScidooAuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Autenticazione Scidoo fallita: {str(e)}"
        ) from e
    except ScidooAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Errore API Scidoo: {str(e)}"
        ) from e
    except Exception as e:
        logger.error(f"Errore configurazione Scidoo per host {host_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore configurazione integrazione Scidoo: {str(e)}"
        ) from e


@router.post(
    "/scidoo/{host_id}/sync",
    response_model=ScidooSyncResponse,
    status_code=status.HTTP_200_OK,
)
def sync_scidoo_reservations(
    host_id: str,
    payload: ScidooSyncRequest,
    firestore_client: firestore.Client = Depends(get_firestore_client),
    persistence_service: PersistenceService = Depends(get_scidoo_persistence_service),
) -> ScidooSyncResponse:
    """
    Esegue import massivo prenotazioni Scidoo.
    
    Se non specificate date, importa ultimi 6 mesi.
    """
    try:
        # Recupera API key
        integrations_repo = ScidooIntegrationsRepository(firestore_client)
        api_key = integrations_repo.get_api_key(host_id)
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Integrazione Scidoo non configurata per host {host_id}"
            )
        
        # Determina range date - usa data di creazione invece di check-in
        if payload.checkin_from and payload.checkin_to:
            # Se vengono passate date, le usiamo come creation_from/creation_to
            creation_from = payload.checkin_from
            creation_to = payload.checkin_to
        else:
            # Default: ultimi 6 mesi basato su data di creazione prenotazione
            creation_from = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
            creation_to = datetime.now().strftime("%Y-%m-%d")
        
        # Chiama API con parametri di creazione
        client = ScidooReservationClient(api_key=api_key, mock_mode=False)
        reservations = client.get_reservations(
            creation_from=creation_from,
            creation_to=creation_to,
        )
        
        logger.info(
            f"[SCIDOO] Sync host {host_id}: trovate {len(reservations)} prenotazioni "
            f"create da {creation_from} a {creation_to}"
        )
        
        # Processa prenotazioni
        processed = 0
        skipped = 0
        errors = 0
        reservation_details = []
        
        for reservation in reservations:
            try:
                save_result = persistence_service.save_scidoo_reservation(reservation, host_id)
                
                if save_result.get("saved"):
                    processed += 1
                    reservation_details.append({
                        "internal_id": reservation.internal_id,
                        "status": "saved",
                        "property_id": save_result.get("property_id"),
                        "client_id": save_result.get("client_id"),
                    })
                elif save_result.get("skipped"):
                    skipped += 1
                    reservation_details.append({
                        "internal_id": reservation.internal_id,
                        "status": "skipped",
                        "reason": "already_exists",
                    })
                else:
                    errors += 1
                    reservation_details.append({
                        "internal_id": reservation.internal_id,
                        "status": "error",
                        "error": save_result.get("error", "unknown"),
                    })
            except Exception as e:
                errors += 1
                logger.error(f"Errore salvataggio prenotazione {reservation.internal_id}: {e}")
                reservation_details.append({
                    "internal_id": reservation.internal_id,
                    "status": "error",
                    "error": str(e),
                })
        
        return ScidooSyncResponse(
            processed=processed,
            skipped=skipped,
            errors=errors,
            reservations=reservation_details,
        )
        
    except ScidooAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Errore API Scidoo: {str(e)}"
        ) from e
    except Exception as e:
        logger.error(f"Errore sync Scidoo per host {host_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore sync prenotazioni Scidoo: {str(e)}"
        ) from e


@router.post(
    "/scidoo/{host_id}/test",
    response_model=ScidooTestResponse,
    status_code=status.HTTP_200_OK,
)
def test_scidoo_connection(
    host_id: str,
    payload: ScidooTestRequest,
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> ScidooTestResponse:
    """
    Testa connessione API Scidoo.
    
    Se api_key è fornita nel body, la usa per il test senza salvare.
    Altrimenti recupera l'API key salvata da Firestore.
    """
    try:
        # Determina API key da usare
        api_key = None
        if payload.api_key:
            # Usa API key fornita nel body (test senza salvataggio)
            api_key = payload.api_key
            logger.info(f"[SCIDOO] Test connessione con API key fornita per host {host_id}")
        else:
            # Recupera API key salvata
            integrations_repo = ScidooIntegrationsRepository(firestore_client)
            api_key = integrations_repo.get_api_key(host_id)
            
            if not api_key:
                return ScidooTestResponse(
                    connected=False,
                    error="API key non configurata. Fornisci un'API key per testare la connessione.",
                )
            logger.info(f"[SCIDOO] Test connessione con API key salvata per host {host_id}")
        
        # Test connessione
        client = ScidooReservationClient(api_key=api_key, mock_mode=False)
        account_info = client.get_account_info()
        
        account_name = account_info.get("name")
        properties = account_info.get("properties", [])
        properties_count = len(properties) if isinstance(properties, list) else 0
        
        return ScidooTestResponse(
            connected=True,
            accountName=account_name,
            propertiesCount=properties_count,
        )
        
    except ScidooAuthenticationError as e:
        return ScidooTestResponse(
            connected=False,
            error=f"Autenticazione fallita: {str(e)}",
        )
    except ScidooAPIError as e:
        return ScidooTestResponse(
            connected=False,
            error=f"Errore API: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Errore test connessione Scidoo per host {host_id}: {e}", exc_info=True)
        return ScidooTestResponse(
            connected=False,
            error=f"Errore: {str(e)}",
        )


@router.get(
    "/scidoo/{host_id}/room-types",
    response_model=ScidooRoomTypesResponse,
    status_code=status.HTTP_200_OK,
)
def get_scidoo_room_types(
    host_id: str,
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> ScidooRoomTypesResponse:
    """
    Recupera lista room types Scidoo per configurazione mapping.
    """
    try:
        # Recupera API key
        integrations_repo = ScidooIntegrationsRepository(firestore_client)
        api_key = integrations_repo.get_api_key(host_id)
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Integrazione Scidoo non configurata per host {host_id}"
            )
        
        # Chiama API
        client = ScidooReservationClient(api_key=api_key, mock_mode=False)
        room_types_data = client.get_room_types()
        
        # Converti in modelli
        room_types = [
            ScidooRoomType(
                id=rt.get("id"),
                name=rt.get("name", ""),
                description=rt.get("description"),
                size=rt.get("size"),
                capacity=rt.get("capacity"),
                additionalBeds=rt.get("additional_beds"),
                images=rt.get("images", []),
            )
            for rt in room_types_data
        ]
        
        return ScidooRoomTypesResponse(roomTypes=room_types)
        
    except ScidooAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Errore API Scidoo: {str(e)}"
        ) from e
    except Exception as e:
        logger.error(f"Errore recupero room types Scidoo per host {host_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore recupero room types: {str(e)}"
        ) from e


@router.delete(
    "/scidoo/{host_id}",
    status_code=status.HTTP_200_OK,
)
def remove_scidoo_integration(
    host_id: str,
    firestore_client: firestore.Client = Depends(get_firestore_client),
) -> dict:
    """
    Rimuove integrazione Scidoo per un host.
    
    Elimina:
    - API key e configurazione
    - Tutte le prenotazioni con importedFrom="scidoo_api"
    - Tutti i clienti con importedFrom="scidoo_api"
    - Tutte le properties con importedFrom="scidoo_api"
    - Tutti i mapping Scidoo property
    """
    try:
        # Inizializza repository
        integrations_repo = ScidooIntegrationsRepository(firestore_client)
        reservations_repo = ReservationsRepository(firestore_client)
        clients_repo = ClientsRepository(firestore_client)
        properties_repo = PropertiesRepository(firestore_client)
        mappings_repo = ScidooPropertyMappingsRepository(firestore_client)
        
        imported_from = "scidoo_api"
        
        # Elimina prenotazioni, clienti e properties importate da Scidoo
        reservations_deleted = reservations_repo.delete_by_imported_from(host_id, imported_from)
        clients_deleted = clients_repo.delete_by_imported_from(host_id, imported_from)
        properties_deleted = properties_repo.delete_by_imported_from(host_id, imported_from)
        mappings_deleted = mappings_repo.delete_by_host(host_id)
        
        # Rimuovi API key e configurazione
        integrations_repo.remove_integration(host_id)
        
        logger.info(
            f"[SCIDOO] Integrazione rimossa per host {host_id}: "
            f"{reservations_deleted} prenotazioni, {clients_deleted} clienti, "
            f"{properties_deleted} properties, {mappings_deleted} mapping eliminati"
        )
        
        return {
            "success": True,
            "message": "Integrazione Scidoo rimossa",
            "deleted": {
                "reservations": reservations_deleted,
                "clients": clients_deleted,
                "properties": properties_deleted,
                "mappings": mappings_deleted,
            }
        }
    except Exception as e:
        logger.error(f"Errore rimozione integrazione Scidoo per host {host_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore durante rimozione: {str(e)}"
        ) from e

