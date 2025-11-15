from typing import TYPE_CHECKING

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from firebase_admin import firestore

from ...dependencies.firebase import get_firestore_client
from ...models import (
    GmailCallbackRequest,
    GmailCallbackResponse,
    GmailIntegrationStartRequest,
    GmailIntegrationStartResponse,
    GmailBackfillResponse,
    GmailWatchRequest,
    GmailWatchResponse,
    GmailNotificationPayload,
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
from ...repositories import HostEmailIntegrationRepository, OAuthStateRepository
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
from ...config.settings import get_settings

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
        pms_provider=payload.pms_provider,
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
            pms_provider=payload.pms_provider,
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
) -> GmailBackfillResponse:
    """
    Esegue il backfill delle email.
    
    Args:
        email: Email dell'integrazione Gmail
        host_id: ID dell'host
        force: Se True, riprocessa anche le email già processate (default: False)
    """
    parsed_results = service.run_backfill(host_id=host_id, email=email, force=force)
    return GmailBackfillResponse(processed=len(parsed_results), items=parsed_results)


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

