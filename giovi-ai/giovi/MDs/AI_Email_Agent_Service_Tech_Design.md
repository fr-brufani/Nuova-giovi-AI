## Servizio Email Concierge AI – Documento Tecnico

### 1. Obiettivo
- **Automatizzare il customer care H24** per i property manager, gestendo conferme prenotazioni e messaggi da Booking/Airbnb.
- **Acquisire le proprietà gestite** analizzando la posta degli ultimi 6 mesi al momento dell’onboarding.
- **Monitorare in tempo reale la casella email** autorizzata e attivare risposte automatiche con Gemini solo per i clienti con toggle `AI on`.

### 2. Stack Tecnologico Proposto
- **Linguaggio**: `Python 3.12`
- **Framework HTTP**: `FastAPI` (endpoints REST + OpenAPI out-of-the-box)
- **Runtime**: `Cloud Run` (build con `Dockerfile`) per scalabilità automatica, oppure `Cloud Functions gen2` se vogliamo delegare il runtime.
- **Scheduler / Job**: `Cloud Scheduler` per refresh watch Gmail e processi periodici.
- **Eventing**: `Pub/Sub` per notifiche Gmail push e code interne (es. pipeline risposta AI).
- **Storage**: `Firestore (modalità Native)` secondo struttura attuale; eventuale `Cloud Storage` per archiviare email raw o allegati pesanti.
- **Secrets**: `Secret Manager` per OAuth client secret, chiavi Gemini, encryption key.
- **Observability**: `Cloud Logging`, `Cloud Trace`, `Error Reporting`; metriche personalizzate via `Cloud Monitoring`.

### 3. Overview Architetturale
- **Frontend (`Clienti` page)**: già presente lo switch `AI on/off` per cliente. Confermato che salva in Firestore via core-service (`/clients/{id}/auto-reply`). Snippet rilevante:

```200:352:giovi-ai/giovi/frontend/giovi-ai-working-app/src/pages/Clienti.tsx
                                  <Switch
                                    checked={autoReplyValue}
                                    className="scale-75"
                                    onCheckedChange={(checked) => handleToggleAI(booking.clientId, checked)}
                                    disabled={toggleDisabled}
                                  />
```

- **Nuovo servizio Python “email-agent-service”**:
  - Espone API per avviare scansione storica e stato integrazione.
  - Gestisce OAuth Gmail; salva token/refresh in `hostEmailIntegrations`.
  - Si sottoscrive a Gmail `watch` e riceve notifiche via Pub/Sub.
  - Esegue pipeline parsing e persistenza prenotazioni/messaggi.
  - Innesca workflow risposta AI (pubblicando job su Pub/Sub).
  - Conserva audit e deduplica via `processedMessageIds`.

- **Core-service esistente**: riusiamo repository Firestore (`clients`, `properties`, `reservations`, …) senza duplicare logica. Il nuovo servizio userà la stessa struttura dati.

### 4. Flussi Chiave

#### 4.1 Onboarding Property Manager
1. L’utente clicca “Connetti casella email” nel portale.
2. Frontend chiama il nuovo endpoint `POST /integrations/gmail/start`, che:
   - genera `state` e URL OAuth Gmail (scope `https://www.googleapis.com/auth/gmail.readonly`, `gmail.modify`, `gmail.send`).
   - salva stato in `oauthStates`.
3. Dopo consent, Google richiama `POST /integrations/gmail/callback`:
   - scambia `code` per access/refresh token (usando `google-auth`).
   - cifra i token e salva record in `hostEmailIntegrations`.
   - imposta `status=connected`, `watchSubscription` nullo.
4. Trigger job asincrono `enqueue_backfill(hostIntegrationId)`.

#### 4.2 Scansione Storica (ultimi 6 mesi)
1. Job `backfill` recupera token e chiama Gmail `messages.list` con query combinata:
   - Booking: `from:(@mchat.booking.com OR reservation@scidoo.com)`
   - Airbnb: `from:(@reply.airbnb.com OR automated@airbnb.com)`
   - `newer_than:180d`.
2. Per ogni message id:
   - Scarica raw (`format=raw`), normalizza MIME -> testo/html.
   - Identifica tipologia usando regex su subject/from.
   - Passa il payload al parser (vedi §5).
   - Genera record `Property` (se sconosciuta) associando `hostId`.
   - Crea/aggiorna `reservations` e `clients`.
   - Registra `processedMessageIds/{messageId}`.
3. Al termine:
   - Avvia `watch` Gmail (vedi §4.3).
   - Aggiorna `hostEmailAuthorizations` con `status=active`, `isEnabled=true`.

#### 4.3 Monitoraggio Continuo
- Ogni integrazione attiva mantiene un `watch` Gmail verso una topic Pub/Sub dedicata (`gmail-notify-{env}`).
- Endpoint `POST /gmail/notifications` (Pub/Sub push) riceve `historyId`.
- Il servizio avvia job `process_history(hostId, historyId)`:
  1. Usa `users.history.list` per delta dal `lastHistoryIdProcessed`.
  2. Scarica solo messaggi nuovi con gli stessi criteri Booking/Airbnb.
  3. Processa come in backfill, aggiornando `lastHistoryIdProcessed`.
- Scheduler rinnova `watch` ogni 24h (Gmail scade in 7 giorni).

#### 4.4 Pipeline Prenotazioni
- Parser produce `ReservationDTO` con:
  - `reservationId` (Booking voucher / Airbnb thread).
  - `propertyExternalId`, `propertyName`.
  - `clientName`, `clientEmail`, `phone`.
  - `startDate`, `endDate`, `total`, `source`.
- Persistenza:
  - `properties`: `users/{hostId}/properties/{propertyId}` (crea se non esiste).
  - `reservations`: `reservations/{reservationId}` con `hostId`, `propertyId`, `clientId`, metadata.
  - `clients`: `clients/{clientId}` con `autoReplyEnabled` default `true`, email booking/airbnb.
  - `gioviAiChatDataset`: append se vogliamo storicizzare conversazioni e prompt.

#### 4.5 Pipeline Messaggi + Risposta AI
1. Parser messaggio produce `GuestMessageDTO`:
   - `bookingId/threadId`, `clientId`, `propertyId`, `timestamp`, `messageText`, `channel`.
2. Salva in `chatMessages` (nuova subcollection `reservations/{id}/messages` oppure collezione dedicata, definire standard).
3. Verifica `clients/{clientId}.autoReplyEnabled`.
4. Se OFF → termina.
5. Se ON → pubblica evento su Pub/Sub `ai-response-jobs`.
6. Worker `ai_responder`:
   - Recupera contesto property (`users/{host}/properties/{property}`) e conversazione pregressa.
   - Costruisce prompt secondo template fornito.
   - Chiamata a Gemini via `google-generativeai` (modello `gemini-1.5-pro`).
   - Applica safety: fallback se errore, ritenta 2 volte, blocca se risposta vuota.
   - Persiste:
     - `gioviAiChatDataset`: store prompt/response, `toolCallPublished`.
     - `chatMessages`: append messaggio `sender='host_ai'`.
   - Invio email reply:
     - Gmail API `users.messages.send` con `threadId` e `replyTo`.
     - header `References` per mantenere thread.
   - Aggiorna `aiResponses` collection con esito (per audit).

### 5. Parsing Email
- **Libreria**: usare `beautifulsoup4`, `python-dateutil`, `pydantic`.
- **Struttura moduli**:
  - `parsers/base.py`: interfaccia comune.
  - `parsers/booking_confirm.py`, `booking_message.py` (sender `@mchat.booking.com`).
  - `parsers/airbnb_confirm.py`, `airbnb_message.py`.
  - `parsers/utils.py`: estrazione campi, normalizzazione valute, quantità, ID.
- **Strategia**:
  - Converte HTML in tabelle/dizionari (vedi guida `Parsing Mail Guida.md`).
  - Identifica ID prenotazione:
    - Booking: subject, body, address `@mchat.booking.com`.
    - Airbnb: `thread` nei link e `reply-to`.
  - Mappa property: usa `Struttura Richiesta` (Booking) o `room link` (Airbnb).
  - Normalizza date con timezone host (di default `Europe/Rome`, override per host).
  - Gestisce deduplica (se mail ritrasmessa).

### 6. Struttura Dati Firestore
- **`hostEmailIntegrations/{email}`**: aggiungere campi:
  - `provider='gmail'`, `historySyncStatus`, `lastBackfillAt`, `watchSubscription.expiry`.
- **`hostEmailAuthorizations/{id}`**: lasciare per tracking manuale; aggiornare `status` e `isEnabled`.
- **`clients/{clientId}`**: già usato, assicurarci che il toggle scriva `autoReplyEnabled`.
- **`reservations/{reservationId}`**: aggiungere `sourceChannel`, `bookingConfirmationId`, `threadId`.
- **Nuove collezioni**:
  - `chatMessages`: `reservations/{resId}/messages/{messageId}` con `sender`, `text`, `timestamp`, `channel`.
  - `aiResponses`: per audit (`requestPayload`, `response`, `status`, `latency`).
- **Referenze**:
  - Conservare `processedMessageIds` come già presente per deduplica.
  - Possibile aggiungere `properties` direttamente sotto `hosts` se non già in uso (rispettiamo struttura attuale in `users/{host}/properties`).

### 7. API del Servizio
- `POST /integrations/gmail/start` → restituisce URL OAuth.
- `POST /integrations/gmail/callback` → completa onboarding.
- `POST /integrations/{integrationId}/backfill` → re-run manuale.
- `POST /gmail/notifications` → endpoint Pub/Sub.
- `POST /messages/manual-reply` → eventuale override umano (futuro).
- `GET /integrations/{integrationId}` → stato (token valido, ultimo historyId).
- Sicurezza: autenticazione via `Firebase Auth` ID token nel frontend → passare a servizio, validare con `firebase-admin`. Ruoli: solo property manager sul proprio hostId.

### 8. Moduli Applicativi
- `api/` (FastAPI routers).
- `services/`:
  - `gmail.py` (OAuth, watch, history, send).
  - `parsing.py`.
  - `reservations.py`, `clients.py`, `properties.py` (Firestore).
  - `ai.py` (Gemini adapter + prompt).
  - `messaging.py` (coda Pub/Sub).
- `workers/`:
  - `backfill_worker`.
  - `history_worker`.
  - `ai_responder`.
- `models/` con `pydantic` DTO.
- `config/` per env (Gemini key, project id, Firestore).
- `infra/` (Dockerfile, CI workflow, Terraform/`gcloud` scripts).

### 9. Prompt Design Gemini
- Template base indicato: includere nome property, regole risposta, fallback “Mi dispiace…”.
- Contesto:
  - `propertyData`: info Firestore (accesso, servizi, WI-FI).
  - `conversationHistory`: ultimi N messaggi (max token 2k).
  - `reservationData`: date, ospiti, eventuali note.
- Sanitizzazione:
  - Rimuovere PII non necessaria, pesi in prompt.
  - Limitare a `language=it` salvo se utente scrive altra lingua (language detection).
- Logging:
  - Salvare prompt (senza dati sensibili) e response in `gioviAiChatDataset`.

### 10. Gestione Errori & Recovery
- **Token scaduti**: se refresh fallisce, settare `status=requires_reauth`, notificare front-end.
- **Parsing fallito**:
  - Salva email raw su GCS bucket `email-agent-errors`.
  - Crea task `propertyTasks` per intervento manuale.
  - Metriche `parsing_failure_count`.
- **AI failure**:
  - Ritenta 2 volte; se fallisce, crea task manuale e invia email fallback al PM.
- **Email send failure**:
  - Logging + `taskType='email_send_retry'`.

### 11. Sicurezza e Compliance
- Token Gmail cifrati con `Fernet` e chiave da Secret Manager.
- Least privilege: scope `gmail.send` solo se auto reply attivo, altrimenti `readonly`.
- Audit log: ogni risposta AI con `hostId`, `clientId`, `reservationId`.
- GDPR: garantire cancellazione su richiesta (flag soft-delete su Firestore + cleanup GCS).

### 12. Roadmap Implementativa
- **S1**: Setup repo, FastAPI skeleton, Firebase Admin client.
- **S2**: OAuth Gmail + salvataggio integrazione.
- **S3**: Backfill 6 mesi + parser Booking/Airbnb (riusare logica di `core-service/src/parsers` come riferimento).
- **S4**: Gmail watch + history worker.
- **S5**: Persistenza prenotazioni/clienti/property.
- **S6**: Pipeline messaggi + Pub/Sub AI jobs.
- **S7**: Gemini integrazione + invio email reply.
- **S8**: Monitoring, tests end-to-end, rollout parziale.

### 13. Testing & QA
- **Strumenti comuni**: `pytest` per unit/integration, `ruff` o `flake8` per lint, emulatori ufficiali (`firebase emulators:start`, `gcloud beta emulators pubsub`) per test locali.
- **Automazione**: tutti i test indicati come “Automazione (terminale)” possono essere lanciati da questo agente tramite comandi (`uv run pytest …`, `npm` per emulatori). Vanno inseriti nella CI.
- **Manuale/Human-in-the-loop**: test che richiedono interazione OAuth reale, account Gmail, console GCP o verifica visuale restano a tuo carico.

#### 13.1 Copertura per Step
- **S1 – Setup repo, FastAPI skeleton, Firebase Admin**
  - Automazione (terminale): lint (`ruff check src`), smoke test FastAPI (`pytest tests/unit/test_health.py` con TestClient).
  - Manuale: nessuno.

- **S2 – OAuth Gmail + salvataggio integrazione**
  - Automazione (terminale): unit test su `gmail_oauth.py` con HTTP mock (`pytest tests/unit/test_gmail_oauth.py`); integration su Firestore emulator (`pytest tests/integration/test_oauth_callback.py` usando `FIRESTORE_EMULATOR_HOST`).
  - Manuale: flusso OAuth reale con account PM per confermare consensi, verificare record in Firestore reale.

- **S3 – Backfill 6 mesi + parser Booking/Airbnb**
  - Automazione (terminale): unit test parser (`pytest tests/parsers/test_booking_confirm.py`, `test_airbnb_confirm.py`) con fixture da `Parsing Mail Guida.md`; integration su emulator per pipeline `backfill_worker`.
  - Manuale: controllare campioni di email non censiti/segnalati dal cliente, aggiornare fixture se cambiano template.

- **S4 – Gmail watch + history worker**
  - Automazione (terminale): unit test su gestione `historyId` e deduplica (`pytest tests/unit/test_history_worker.py`); integration con Pub/Sub emulator (`pytest tests/integration/test_gmail_notification.py`).
  - Manuale: verifica su GCP che il `watch` venga creato/rinnovato (console Gmail API), test push reale su topic Pub/Sub (richiede ambiente cloud).

- **S5 – Persistenza prenotazioni/clienti/property**
  - Automazione (terminale): integration `pytest tests/integration/test_firestore_writes.py` con emulator (verifica schema, referenze, deduplica).
  - Manuale: validazione dati su Firestore reale prima del go-live (spot check).

- **S6 – Pipeline messaggi + Pub/Sub AI jobs**
  - Automazione (terminale): unit test orchestratore (`pytest tests/unit/test_message_router.py`), integration con Pub/Sub emulator (`pytest tests/integration/test_message_pipeline.py`).
  - Manuale: test con conversazione reale (Booking/Airbnb) per assicurare mapping ID → cliente; richiede dati veri.

- **S7 – Gemini integrazione + invio email reply**
  - Automazione (terminale): unit test prompt (`pytest tests/unit/test_prompt_builder.py`), contract test con stub Gemini (`pytest tests/integration/test_gemini_adapter.py`), unit per `gmail_send` con mock.
  - Manuale: invio risposta reale su sandbox Gmail / property manager, review qualitativa delle risposte AI, verifica deliverability (DKIM/SPF).

- **S8 – Monitoring, E2E, rollout**
  - Automazione (terminale): e2e controllato con emulatori (`pytest tests/e2e/test_full_flow.py` avviando emulatori in background), load test locale con `locust`/`k6` su endpoint notifiche.
  - Manuale: smoke test in staging con account Gmail reale, verifica dashboard Cloud Monitoring e alerting, prova failover (token scaduto) in ambiente controllato.

#### 13.2 Altre Verifiche
- **Load Test**: scenario 100 notifiche/min con `k6 run k6/email_notifications.js` (eseguibile dal terminale).
- **Security Test**: test automatizzabili con `pytest tests/security/test_authz.py` + `bandit` per static analysis; penetration test manuale opzionale in staging.
- **Regression Suite CI**: pipeline GitHub Actions/Cloud Build che lancia `uv run ruff check`, `uv run pytest -m "not e2e"`, e su trigger notturno `pytest -m e2e` con emulatori.

### 14. Variabili d’Ambiente Chiave
- `TOKEN_ENCRYPTION_KEY`: chiave base64 32-byte (Fernet) per cifrare access/refresh token Gmail.
- `GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`: credenziali OAuth da console Google Cloud → consent screen interno.
- `GOOGLE_OAUTH_REDIRECT_URI`: callback pubblico impostato su Google Cloud (es. `https://api.giovi.ai/email-agent/oauth/callback`).
- `GOOGLE_OAUTH_SCOPES`: opzionale, lista (JSON o CSV) per personalizzare gli scope OAuth; default include `gmail.modify`, `gmail.send`, `gmail.readonly`.
- `FIREBASE_CREDENTIALS_PATH` o `FIREBASE_CREDENTIALS_JSON`: scelta unica per inizializzare Firebase Admin (service account).
- `FIREBASE_PROJECT_ID`: forza il target project se non deducibile dallo user account.

### 15. Considerazioni Finali
- Il servizio è indipendente dai microservizi legacy; possiamo spegnere gradualmente workflow duplicati.
- Necessario predisporre **migrazione** per aggiungere `autoReplyEnabled` ai clienti esistenti (default true).
- La pagina `Clienti` è già pronta ad usare il toggle, dobbiamo assicurare l’endpoint `PATCH /clients/{id}/auto-reply` nel core-service sia mantenuto o replicato nel nuovo servizio (federare logica).
- Il documento fungerà da blueprint per implementazione, con priorità a onboarding + parsing + auto-reply pipeline.

