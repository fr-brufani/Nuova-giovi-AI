# Analisi Integrazione Booking.com Messaging API

## 📋 Executive Summary

Analisi completa della documentazione Booking.com API e piano di sviluppo per integrare:
1. **Import automatico delle prenotazioni** quando vengono create (Reservation API)
2. **Risposta automatica ai messaggi** tramite AI (Messaging API + Gemini)

Il sistema funzionerà come per Airbnb ma utilizzando direttamente le API ufficiali di Booking.com invece del parsing email.

**Data analisi:** 2025-01-15  
**Stato documentazione:** ✅ Completa e sufficiente per implementazione

---

## 🔍 Analisi Documentazione API

### ✅ Informazioni Disponibili

La documentazione in `api_doc_booking/` contiene tutte le informazioni necessarie per implementare l'integrazione:

#### **Messaging API** (`messaging_api/`)
1. **Understanding the Messaging API** ✅
   - Overview completa delle funzionalità
   - Supporto per self-service requests (v1.2)
   - Limitazioni e best practices

2. **Managing messages** ✅
   - `GET /messages/latest` - Recupero messaggi dalla coda (max 100 per chiamata)
   - `PUT /messages` - Conferma recupero messaggi (per rimuoverli dalla coda)
   - Versioning (v1.0 default, v1.2 per self-service)
   - Gestione code duplicate

3. **Managing conversations** ✅
   - `POST /properties/{property_id}/conversations/{conversation_id}` - Invia messaggio
   - `GET /properties/{property_id}/conversations` - Lista tutte le conversazioni
   - `GET /properties/{property_id}/conversations/{conversation_id}` - Dettagli conversazione per ID
   - `GET /properties/{property_id}/conversations/type/{conversation_type}` - Conversazione per reservation_id

4. **Managing tags** ✅
   - `PUT /.../tags/no_reply_needed` - Marca come "no reply needed"
   - `PUT /.../tags/message_read` - Marca messaggi come letti
   - `DELETE` per rimuovere tag

5. **Searching messages** ✅
   - `GET /messages/search` - Crea query per recuperare messaggi storici
   - `GET /messages/search/result/{job_id}` - Recupera risultati query
   - Utile per backfill o recupero messaggi persi

6. **Uploading and downloading attachments** ✅
   - Upload allegati < 1MB (single request)
   - Upload allegati 1-10MB (chunked)
   - Download allegati
   - Supporto solo immagini (JPEG/PNG)

7. **Troubleshooting and error codes** ✅
   - Lista errori HTTP comuni (401, 403, 429, 500)
   - Soluzioni per ogni tipo di errore

8. **Use cases and best practices** ✅
   - Flussi per property che inizia conversazione
   - Flussi per guest che inizia conversazione
   - Pattern con/senza salvataggio messaggi in locale

9. **Version history** ✅
   - v1.0 (default): funzionalità base
   - v1.2: supporto self-service requests, message_type, guest name, attributes

#### **Reservation API** (`reservation_api/`)
1. **Understanding the Reservations API** ✅
   - Overview sistema di delivery prenotazioni
   - OTA XML vs B.XML endpoints
   - Fallback mechanism (email se non recuperate entro 30 min)

2. **Retrieving new reservations** ✅
   - `GET /OTA_HotelResNotif` - Recupera nuove prenotazioni (XML OTA)
   - `POST /OTA_HotelResNotif` - Conferma processamento
   - Polling raccomandato: ogni 20 secondi
   - Attesa 5 secondi tra POST e successivo GET

3. **Retrieving modified or cancelled reservations** ✅
   - `GET /OTA_HotelResModifyNotif` - Recupera modifiche/cancellazioni
   - `POST /OTA_HotelResModifyNotif` - Conferma processamento

4. **Acknowledging reservations** ✅
   - Pattern GET → processa → POST acknowledgement
   - Elimina prenotazioni dalla coda
   - Previene fallback email

5. **General information** ✅
   - Reservation hold per manutenzione
   - Fallback emails se non recuperate entro timeout
   - Transliteration support

**Endpoint principali:**
- Base URL: `https://secure-supply-xml.booking.com/hotels/ota/`
- `GET /OTA_HotelResNotif` - Nuove prenotazioni
- `POST /OTA_HotelResNotif` - Acknowledgement
- `GET /OTA_HotelResModifyNotif` - Modifiche/cancellazioni
- `POST /OTA_HotelResModifyNotif` - Acknowledgement

### ⚠️ Informazioni Mancanti da Verificare

1. **Autenticazione specifica**:
   - ✅ Documentazione menziona "same authentication as other APIs"
   - ⚠️ Necessario verificare formato esatto (Basic Auth con username/password o token)
   - ⚠️ Come ottenere credenziali Machine Account
   - ⚠️ Dove configurare accesso a `/messages/latest` endpoint

2. **Provider Portal**:
   - ⚠️ Accesso necessario per:
     - Abilitare feature `enable_self_services_messaging`
     - Gestire Machine Accounts
     - Verificare connessioni proprietà

3. **Rate Limits**:
   - ✅ Documentazione menziona rate limits ma non specifica numeri esatti
   - ⚠️ Necessario verificare durante implementazione

4. **Webhook/Notifications**:
   - ✅ Documentazione menziona "Connectivity Notification Service" come deprecazione alternativa a polling
   - ⚠️ Necessario valutare se implementare webhook invece di polling

---

## 🎯 Confronto con Implementazione Airbnb Attuale

### **Airbnb (Attuale - Email-based)**

#### **Import Prenotazioni:**
```
Email Gmail → BookingConfirmationParser → Salva in Firestore
```

#### **Risposta Messaggi:**
```
Email Gmail → BookingMessageParser → GuestMessagePipeline → GeminiService → Reply via Email
```

**Componenti:**
- `BookingConfirmationParser`: estrae dati prenotazione da email
- `BookingMessageParser`: estrae messaggio da email
- `GmailWatchService`: monitora nuovi messaggi via Gmail Push
- `GuestMessagePipelineService`: determina se processare, estrae contesto
- `GeminiService`: genera risposta AI
- Reply via email SendGrid/Gmail

**Vantaggi:**
- ✅ Non richiede credenziali Booking.com API
- ✅ Funziona con qualsiasi email Booking

**Svantaggi:**
- ❌ Dipendenza da parsing email (fragile)
- ❌ Limitato a formati email che possiamo parsare
- ❌ Non supporta funzionalità avanzate API (self-service, tags, etc.)
- ❌ Import prenotazioni dipendente da email (può arrivare in ritardo o non arrivare)

### **Booking.com (Nuovo - API-based)**

#### **Import Prenotazioni:**
```
Booking Reservation API → Polling Service → Parser XML → Salva in Firestore
```

#### **Risposta Messaggi:**
```
Booking Messaging API → Polling Service → GuestMessagePipeline → GeminiService → Reply via Booking API
```

**Componenti necessari:**

**Per prenotazioni:**
- `BookingReservationClient`: client Reservation API
- `BookingReservationPollingService`: polling `/OTA_HotelResNotif` ogni 20s
- `BookingReservationParser`: parser XML OTA → formato interno
- `PersistenceService`: salva prenotazioni in Firestore

**Per messaggi:**
- `BookingMessagingClient`: client Messaging API
- `BookingMessagePollingService`: polling `/messages/latest`
- `GuestMessagePipelineService`: (riutilizzare esistente con estensioni)
- `GeminiService`: (riutilizzare esistente)
- `BookingReplyService`: invia risposta via Booking API

**Vantaggi:**
- ✅ Integrazione ufficiale e stabile
- ✅ Import prenotazioni in tempo reale (polling ogni 20s)
- ✅ Supporto completo funzionalità messaging (self-service, tags, attachments)
- ✅ Non dipendente da formati email
- ✅ Più affidabile e manutenibile

**Svantaggi:**
- ❌ Richiede credenziali Machine Account Booking.com
- ❌ Necessario polling periodico (o webhook se disponibile)
- ❌ Parsing XML OTA (più complesso di JSON ma ben documentato)

---

## 📐 Architettura Proposta

### **Architettura High-Level**

#### **Flusso 1: Import Prenotazioni Automatico**

```
┌─────────────────────────────────────────────────────────────┐
│           Booking.com Reservation API                       │
│  (OTA XML: /OTA_HotelResNotif)                             │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ GET ogni 20s
                        ▼
┌─────────────────────────────────────────────────────────────┐
│      BookingReservationPollingService                       │
│  - Polling periodico (ogni 20 secondi)                     │
│  - Recupera nuove prenotazioni                              │
│  - Recupera modifiche/cancellazioni                         │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ XML OTA Response
                        ▼
┌─────────────────────────────────────────────────────────────┐
│      BookingReservationParser                               │
│  - Parse XML OTA → formato interno                          │
│  - Estrae: reservation_id, property_id, dates, guest info   │
│  - Gestisce commissioni, pagamenti, VCC, etc.               │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ Reservation Data
                        ▼
┌─────────────────────────────────────────────────────────────┐
│      PersistenceService                                     │
│  - Salva in Firestore (reservations collection)             │
│  - Crea/aggiorna client se necessario                       │
│  - Collega a property                                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ POST acknowledgement
                        ▼
┌─────────────────────────────────────────────────────────────┐
│      BookingReservationPollingService                       │
│  - Conferma processamento (POST /OTA_HotelResNotif)         │
│  - Rimuove dalla coda                                       │
└─────────────────────────────────────────────────────────────┘
```

#### **Flusso 2: Risposta Automatica ai Messaggi**

```
┌─────────────────────────────────────────────────────────────┐
│           Booking.com Messaging API                         │
│  (/messages/latest)                                         │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ GET /messages/latest (polling ogni 30s-1min)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│         BookingMessagePollingService                        │
│  - Polling periodico                                        │
│  - Conferma messaggi (PUT /messages)                        │
│  - Gestione code e deduplicazione                           │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ Messaggi nuovi
                        ▼
┌─────────────────────────────────────────────────────────────┐
│         BookingMessageProcessor                             │
│  - Normalizza formato Booking → formato interno             │
│  - Estrae reservation_id, property_id, guest info           │
│  - Filtra solo messaggi guest (participant_type: "GUEST")   │
│  - Salva in Firestore (conversations)                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ ParsedMessage (formato interno)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│         GuestMessagePipelineService                         │
│  (Riutilizzare esistente con estensioni Booking)            │
│  - Verifica autoReplyEnabled                                │
│  - Estrae contesto (property, reservation, client)          │
│  - Recupera conversazione precedente                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ GuestMessageContext
                        ▼
┌─────────────────────────────────────────────────────────────┐
│         GeminiService                                       │
│  (Riutilizzare esistente)                                   │
│  - Genera risposta AI                                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ AI Reply Text
                        ▼
┌─────────────────────────────────────────────────────────────┐
│         BookingReplyService                                 │
│  - Recupera conversation_id da reservation_id               │
│  - Invia risposta via POST /conversations/{id}              │
│  - Opzionale: marca come letta (PUT /tags/message_read)     │
│  - Opzionale: upload allegati se presenti                   │
└─────────────────────────────────────────────────────────────┘
```

### **Nuovi Moduli da Creare**

#### **Per Prenotazioni:**
1. **`services/integrations/booking_reservation_client.py`** - Client Reservation API
2. **`services/booking_reservation_polling_service.py`** - Polling prenotazioni
3. **`parsers/booking_reservation_parser.py`** - Parser XML OTA → formato interno
4. **`models/booking_reservation.py`** - Modelli dati prenotazioni Booking.com

#### **Per Messaggi:**
1. **`services/integrations/booking_messaging_client.py`** - Client Messaging API
2. **`services/booking_message_polling_service.py`** - Polling messaggi
3. **`services/booking_message_processor.py`** - Processore messaggi Booking → formato interno
4. **`services/booking_reply_service.py`** - Servizio invio risposte
5. **`models/booking_message.py`** - Modelli dati messaggi Booking.com

### **Moduli da Estendere**

1. **`guest_message_pipeline.py`** - Aggiungere supporto per `source="booking_api"`
2. **`config/settings.py`** - Aggiungere configurazione Booking.com API (Reservation + Messaging)
3. **`repositories/reservations.py`** - Estendere per supportare formato Booking.com
4. **`services/persistence_service.py`** - Estendere per salvare prenotazioni Booking.com

---

## 📝 Piano di Sviluppo Dettagliato

### **Fase 0: Setup Preliminare** (1-2 giorni)

#### 0.1 Credenziali e Accesso
- [ ] Ottenere credenziali Machine Account Booking.com
- [ ] Verificare accesso Provider Portal
- [ ] Abilitare accesso a `/messages/latest` endpoint (Messaging API)
- [ ] Verificare accesso a Reservation API endpoints
- [ ] (Opzionale) Abilitare feature `enable_self_services_messaging`
- [ ] Verificare property IDs disponibili per testing

---

### **Fase 1: Setup e Client API Base** (4-5 giorni)

#### 1.1 Configurazione e Credenziali
- [ ] Creare sezione configurazione Booking.com in `config/settings.py`
  - **Messaging API:**
    - `BOOKING_MESSAGING_API_BASE_URL`: `https://supply-xml.booking.com/messaging`
    - `BOOKING_API_VERSION`: `1.2` (per supportare self-service)
  - **Reservation API:**
    - `BOOKING_RESERVATION_API_BASE_URL`: `https://secure-supply-xml.booking.com/hotels/ota/`
  - **Credenziali comuni:**
    - `BOOKING_API_USERNAME`: username Machine Account
    - `BOOKING_API_PASSWORD`: password Machine Account

#### 1.2 Client Messaging API Base
- [ ] Creare `services/integrations/booking_messaging_client.py`
  - Classe `BookingMessagingClient`
  - Metodo `authenticate()` - Basic Auth setup
  - Metodo `_request()` - wrapper per richieste HTTP con retry, error handling
  - Gestione versioning via header `Accept-Version: 1.2`
  - Gestione rate limiting (HTTP 429)

#### 1.3 Client Reservation API Base
- [ ] Creare `services/integrations/booking_reservation_client.py`
  - Classe `BookingReservationClient`
  - Metodo `authenticate()` - Basic Auth setup (stesso formato Messaging API)
  - Metodo `_request()` - wrapper per richieste HTTP con retry, error handling
  - Gestione XML responses
  - Metodi per:
    - `get_new_reservations()` - GET /OTA_HotelResNotif
    - `acknowledge_reservations()` - POST /OTA_HotelResNotif
    - `get_modified_reservations()` - GET /OTA_HotelResModifyNotif
    - `acknowledge_modified_reservations()` - POST /OTA_HotelResModifyNotif

#### 1.4 Modelli Dati Messaging
- [ ] Creare `models/booking_message.py`
  - `BookingMessage` - rappresenta messaggio API
  - `BookingConversation` - rappresenta conversazione API
  - `BookingSender` - sender info
  - Funzioni di conversione: `booking_message_to_internal()`

#### 1.5 Modelli Dati Reservation
- [ ] Creare `models/booking_reservation.py`
  - `BookingReservation` - rappresenta prenotazione OTA XML
  - `BookingGuestInfo` - info guest/booker
  - `BookingPaymentInfo` - info pagamento/VCC
  - Funzioni di conversione: `booking_reservation_to_internal()`

**Endpoint da implementare:**
- **Messaging:** `GET /messages/latest`, `PUT /messages` ✅
- **Reservation:** `GET /OTA_HotelResNotif`, `POST /OTA_HotelResNotif` ✅

**File da creare:**
- `src/email_agent_service/services/integrations/booking_messaging_client.py`
- `src/email_agent_service/services/integrations/booking_reservation_client.py`
- `src/email_agent_service/models/booking_message.py`
- `src/email_agent_service/models/booking_reservation.py`

---

### **Fase 2: Import Automatico Prenotazioni** (5-6 giorni)

#### 2.1 Polling Service Prenotazioni
- [ ] Creare `services/booking_reservation_polling_service.py`
  - Classe `BookingReservationPollingService`
  - Metodo `start_polling()` - avvia loop polling
  - Metodo `poll_new_reservations()` - chiama `GET /OTA_HotelResNotif`
  - Metodo `poll_modified_reservations()` - chiama `GET /OTA_HotelResModifyNotif`
  - Metodo `acknowledge_reservations()` - chiama `POST /OTA_HotelResNotif` dopo processamento
  - Intervallo polling: **ogni 20 secondi** (raccomandato Booking.com)
  - Attesa 5 secondi tra POST acknowledgement e successivo GET

#### 2.2 Parser XML OTA
- [ ] Creare `parsers/booking_reservation_parser.py`
  - Classe `BookingReservationParser`
  - Metodo `parse_ota_xml()` - parse XML OTA → formato interno
  - Estrazione dati:
    - `reservation_id` da `ResGlobalInfo > HotelReservationIDs > HotelReservationID > ResID_Value`
    - `property_id` da `RoomStay > BasicPropertyInfo > HotelCode`
    - `check_in/check_out` da `RoomStay > RoomRate > EffectiveDate`
    - `guest_name`, `guest_email`, `guest_phone` da `ResGlobalInfo > Profiles`
    - `total_amount`, `currency` da `ResGlobalInfo > Total`
    - `adults`, `children` da `RoomStay > GuestCounts`
    - `VCC details` (se Payments by Booking)
    - `commission` da `RoomStay > RatePlans > Commission`
  - Gestione multi-room reservations
  - Gestione modifiche e cancellazioni

#### 2.3 Integrazione con Persistence
- [ ] Estendere `services/persistence_service.py` o creare nuovo servizio
  - Metodo `save_booking_reservation()` - salva prenotazione in Firestore
  - Mapping Booking.com → formato Firestore esistente:
    - `reservationId` → `reservationId`
    - `propertyId` (Booking hotel code) → `propertyId` (verificare mapping)
    - Guest info → crea/aggiorna `client`
    - Date → `stayPeriod: { start, end }`
    - `channel: "booking"`
    - `source: { provider: "booking-api", externalId: reservation_id }`
  - Gestione client: crea se non esiste, usa email come identificatore

#### 2.4 Mapping Property IDs
- [ ] Gestire mapping Booking.com property_id → nostro property_id
  - Opzione A: Table mapping in Firestore
  - Opzione B: Usare property_id Booking.com direttamente (se allineati)
  - Verificare con host come sono mappati i property

**File da creare:**
- `src/email_agent_service/services/booking_reservation_polling_service.py`
- `src/email_agent_service/parsers/booking_reservation_parser.py`

**File da modificare:**
- `src/email_agent_service/services/persistence_service.py`
- `src/email_agent_service/repositories/reservations.py`

---

### **Fase 3: Polling e Processamento Messaggi** (4-5 giorni)

#### 2.1 Polling Service
- [ ] Creare `services/booking_polling_service.py`
  - Classe `BookingMessagePollingService`
  - Metodo `start_polling()` - avvia loop polling
  - Metodo `poll_messages()` - chiama `/messages/latest`
  - Metodo `confirm_messages()` - chiama `PUT /messages` dopo processamento
  - Gestione code duplicate (usare `processed_message_ids` in Firestore)
  - Intervallo polling: 30-60 secondi (configurabile)

#### 3.2 Message Processor
- [ ] Creare `services/booking_message_processor.py`
  - Classe `BookingMessageProcessor`
  - Metodo `process_message()` - converte Booking → formato interno
  - Estrazione:
    - `reservation_id` da `conversation.conversation_reference`
    - `property_id` da `conversation` o messaggio
    - `guest_name` da `sender.metadata.name` (v1.2)
    - `message_type` e `attributes` (v1.2)
  - Filtro messaggi: solo `participant_type: "GUEST"`
  - Filtro `message_type`: ignorare `automatically_sent_template` (opzionale)

#### 3.3 Integrazione con Pipeline Esistente
- [ ] Estendere `GuestMessagePipelineService`
  - Aggiungere supporto `source="booking_api"`
  - Modificare `should_process_message()` per accettare formato Booking
  - Modificare `extract_context()` per mappare `conversation_reference` → `reservation_id`

**File da creare:**
- `src/email_agent_service/services/booking_polling_service.py`
- `src/email_agent_service/services/booking_message_processor.py`

**File da modificare:**
- `src/email_agent_service/services/guest_message_pipeline.py`

---

### **Fase 4: Invio Risposte** (3-4 giorni)

#### 4.1 Reply Service
- [ ] Creare `services/booking_reply_service.py`
  - Classe `BookingReplyService`
  - Metodo `send_reply()` - invia messaggio via API
  - Metodo `get_conversation_id()` - recupera conversation_id da reservation_id (se necessario)
  - Gestione errori (403 property access, etc.)

#### 4.2 Integrazione con GeminiService
- [ ] Modificare flow esistente per usare `BookingReplyService` invece di SendGrid quando `source="booking_api"`
- [ ] In `app.py` o route handler, dopo `GeminiService.generate_reply()`:
  - Se `source="booking_api"`: chiama `BookingReplyService.send_reply()`
  - Altrimenti: usa SendGrid (esistente)

#### 4.3 Tag Management (Opzionale - Enhancement)
- [ ] Implementare tagging messaggi come letti dopo invio risposta
  - `PUT /tags/message_read`
- [ ] (Future) Tag `no_reply_needed` se gestito da AI

**Endpoint da implementare:**
- `GET /properties/{property_id}/conversations/type/reservation` ✅ (recupera conversation_id)
- `POST /properties/{property_id}/conversations/{conversation_id}` ✅ (invia messaggio)
- `PUT /properties/{property_id}/conversations/{conversation_id}/tags/message_read` ✅ (opzionale)

**File da creare:**
- `src/email_agent_service/services/booking_reply_service.py`

**File da modificare:**
- `src/email_agent_service/app.py` o route handler per messaging

---

### **Fase 5: Persistenza e Deduplicazione** (2-3 giorni)

#### 5.1 Repository per Messaggi Booking
- [ ] Creare `repositories/booking_messages.py` (opzionale)
  - Tracking messaggi processati
  - Deduplicazione via `message_id`
  - Storage in `processedBookingMessages` collection

#### 5.2 Salvataggio in Firestore
- [ ] Salvare messaggi in conversazioni Firestore (stessa struttura esistente)
  - `properties/{propertyId}/conversations/{clientId}/messages`
  - Campo `source: "booking_api"`
  - Campo `bookingMessageId` per tracking

#### 5.3 Backfill (Opzionale)
- [ ] Implementare backfill messaggi storici usando `/messages/search`
  - Endpoint per triggerare backfill
  - Recupero messaggi fino a 90 giorni fa
  - Processamento batch

**File da creare:**
- `src/email_agent_service/repositories/booking_messages.py` (opzionale)

**File da modificare:**
- `src/email_agent_service/services/persistence_service.py` (se esiste)

---

### **Fase 6: Testing e Error Handling** (4-5 giorni)

#### 6.1 Unit Tests
- [ ] Test `BookingMessagingClient`
  - Mock API responses
  - Test autenticazione
  - Test error handling (401, 403, 429, 500)
- [ ] Test `BookingMessageProcessor`
  - Test conversione formati
  - Test estrazione dati
- [ ] Test `BookingReplyService`
  - Test invio messaggi
  - Test recupero conversation_id

#### 6.2 Integration Tests
- [ ] Test end-to-end con Booking.com sandbox/test environment
- [ ] Test polling → processamento → risposta
- [ ] Test deduplicazione messaggi

#### 6.3 Error Handling Robusto
- [ ] Gestione rate limiting (429) con exponential backoff
- [ ] Gestione timeout API
- [ ] Retry logic per errori temporanei
- [ ] Logging dettagliato per debugging

**File da creare:**
- `tests/unit/test_booking_client.py`
- `tests/unit/test_booking_processor.py`
- `tests/integration/test_booking_flow.py`

---

### **Fase 7: Deployment e Monitoring** (2 giorni)

#### 7.1 Configurazione Produzione
- [ ] Variabili ambiente produzione
- [ ] Secret Manager per credenziali Booking.com
- [ ] Configurazione polling interval

#### 7.2 Monitoring
- [ ] Logging strutturato per tracking messaggi
- [ ] Metriche: messaggi ricevuti, risposte inviate, errori
- [ ] Alert su errori continui o rate limit

#### 7.3 Documentazione
- [ ] README per setup Booking.com API
- [ ] Documentazione endpoint (se esposti)
- [ ] Troubleshooting guide

---

## 🔄 Flussi Completi Implementazione

### **Flow 1: Import Automatico Prenotazione**

```
1. BookingReservationPollingService.poll_new_reservations()
   └─> BookingReservationClient.get_new_reservations()
       └─> GET /OTA_HotelResNotif
       └─> Ritorna XML con prenotazioni

2. Per ogni prenotazione XML:
   BookingReservationParser.parse_ota_xml(xml_response)
   └─> Estrae reservation_id, property_id, guest info, dates, totals
   └─> Converte in formato interno Reservation

3. PersistenceService.save_booking_reservation(booking_reservation)
   └─> Cerca property_id mapping (se necessario)
   └─> Crea/aggiorna client usando guest email
   └─> Salva prenotazione in Firestore:
       - reservations/{reservation_id}
       - properties/{property_id}
       - clients/{client_id}

4. BookingReservationPollingService.acknowledge_reservations()
   └─> POST /OTA_HotelResNotif con reservation IDs
   └─> Rimuove prenotazioni dalla coda
   └─> Previene fallback email
```

### **Flow 2: Ricezione e Risposta Messaggio**

```
1. BookingMessagePollingService.poll_messages()
   └─> BookingMessagingClient.get_latest_messages()
       └─> GET /messages/latest
       └─> Ritorna lista messaggi

2. Per ogni messaggio:
   BookingMessageProcessor.process_message(booking_message)
   └─> Estrae reservation_id, property_id, guest_name
   └─> Converte in formato interno

3. GuestMessagePipelineService.should_process_message()
   └─> Verifica autoReplyEnabled
   └─> Ritorna True/False

4. Se True:
   GuestMessagePipelineService.extract_context()
   └─> Recupera property, reservation, client da Firestore
   └─> Recupera conversazione precedente

5. GeminiService.generate_reply(context, guest_message)
   └─> Genera risposta AI

6. BookingReplyService.send_reply()
   └─> BookingMessagingClient.get_conversation_by_reservation(reservation_id)
       └─> GET /properties/{property_id}/conversations/type/reservation?conversation_reference={reservation_id}
   └─> BookingMessagingClient.send_message(conversation_id, reply_text)
       └─> POST /properties/{property_id}/conversations/{conversation_id}
   └─> (Opzionale) Marca come letta
       └─> PUT /tags/message_read

7. BookingMessagePollingService.confirm_messages()
   └─> PUT /messages?number_of_messages={count}
   └─> Rimuove messaggi dalla coda
```

---

## 📊 Stima Tempi e Risorse

| Fase | Tempo Stimato | Priorità |
|------|---------------|----------|
| Fase 0: Setup Preliminare | 1-2 giorni | Alta |
| Fase 1: Setup e Client API Base | 4-5 giorni | Alta |
| Fase 2: Import Automatico Prenotazioni | 5-6 giorni | Alta |
| Fase 3: Polling e Processamento Messaggi | 4-5 giorni | Alta |
| Fase 4: Invio Risposte | 3-4 giorni | Alta |
| Fase 5: Persistenza | 2-3 giorni | Media |
| Fase 6: Testing | 4-5 giorni | Alta |
| Fase 7: Deployment | 2 giorni | Media |
| **TOTALE** | **25-32 giorni** | |

**Note:**
- Stima per sviluppatore con esperienza API integrations
- Include testing base ma non testing estensivo
- Non include tempo per ottenere credenziali/approvazioni Booking.com
- Fase 2 (Import Prenotazioni) può essere sviluppata in parallelo con Fase 3-4 (Messaggi) se due sviluppatori
- Parsing XML OTA può richiedere più tempo del previsto se struttura complessa

---

## ⚠️ Rischi e Considerazioni

### **Rischi Tecnici**

1. **Rate Limiting Booking.com API**
   - **Rischio**: Polling troppo frequente può causare rate limit
   - **Mitigazione**: Implementare backoff esponenziale, rispettare intervalli raccomandati (30-60s)

2. **Autenticazione Machine Account**
   - **Rischio**: Credenziali non disponibili o formattate diversamente
   - **Mitigazione**: Verificare formato esatto con Booking.com Connectivity Support

3. **Mappatura Property ID**
   - **Rischio**: Property ID Booking.com potrebbero non corrispondere ai nostri property_id
   - **Mitigazione**: Creare mapping table in Firestore se necessario

### **Rischi Funzionali**

1. **Duplicazione Messaggi**
   - **Rischio**: Messaggi duplicati se polling e email processing attivi simultaneamente
   - **Mitigazione**: 
     - Disabilitare parsing email Booking quando API attiva
     - Deduplicazione tramite `message_id` o `gmail_message_id`

2. **Conversazioni Multiple**
   - **Rischio**: Più conversazioni per stessa reservation
   - **Mitigazione**: Verificare documentazione su unicità conversazioni

### **Considerazioni Architetturali**

1. **Polling vs Webhook**
   - **Attuale**: Polling periodico
   - **Future**: Valutare Connectivity Notification Service (webhook) se disponibile

2. **Coesistenza Email e API**
   - Permettere entrambi i metodi per transizione graduale
   - Flag in configurazione per abilitare/disabilitare ciascun metodo

---

## 📋 Checklist Pre-Implementazione

Prima di iniziare lo sviluppo, verificare:

- [ ] Credenziali Machine Account Booking.com disponibili
- [ ] Accesso Provider Portal per configurazione
- [ ] Accesso a `/messages/latest` endpoint abilitato per Machine Account
- [ ] Test property disponibile per testing
- [ ] Comunicazione con Booking.com Connectivity Support stabilita
- [ ] Documentazione ufficiale più recente verificata (potrebbero esserci aggiornamenti)

---

## 🔗 Riferimenti

### **Documentazione Interna**
- `/giovi-ai/email-agent-service/README.md` - Setup servizio esistente
- `/giovi-ai/email-agent-service/src/email_agent_service/services/guest_message_pipeline.py` - Pipeline esistente

### **API Booking.com**
- Base URL: `https://supply-xml.booking.com/messaging`
- Versioning: Header `Accept-Version: 1.2`
- Auth: Basic Authentication (username:password)

### **Endpoint Principali**
- `GET /messages/latest` - Recupera nuovi messaggi
- `PUT /messages?number_of_messages={n}` - Conferma recupero
- `POST /properties/{property_id}/conversations/{conversation_id}` - Invia messaggio
- `GET /properties/{property_id}/conversations/type/reservation?conversation_reference={reservation_id}` - Recupera conversazione

---

## 🧪 Come Testare l'Integrazione

Una volta sviluppata l'integrazione, ecco come testarla seguendo la documentazione Booking.com:

### **Prerequisiti per il Testing**

1. **Test Property**:
   - Avere una property di test con connessione attiva nel Provider Portal
   - La property deve avere almeno una room type con availability e prezzi
   - Property ID disponibile per testing

2. **Credenziali**:
   - Machine Account Booking.com configurato
   - Accesso a `/messages/latest` endpoint abilitato
   - Accesso a Reservation API endpoints verificato

3. **Environment**:
   - API URLs: Booking.com usa lo stesso ambiente per test e produzione
   - URL test reservations: `https://secure.booking.com/book.html?test=1;hotel_id={property_id}`

---

### **Testing Messaging API**

#### **Step 1: Crea Test Reservations**

1. Vai a: `https://secure.booking.com/book.html?test=1;hotel_id={property_id}`
   - Sostituisci `{property_id}` con il tuo property ID di test

2. **Reservation 1**: Crea una prenotazione e come guest invia un messaggio alla property
   - Durante la prenotazione o dopo, invia un messaggio usando l'app o desktop Booking.com
   - Questo crea una conversazione con messaggio guest

3. **Reservation 2**: Crea un'altra prenotazione ma NON inviare messaggi come guest
   - Questa sarà una conversazione vuota per testare property che inizia conversazione

#### **Step 2: Testa Polling Messaggi**

```bash
# Avvia il polling service
python -m email_agent_service.services.booking_message_polling_service

# Verifica nei log:
# - Messaggi recuperati da /messages/latest
# - Messaggi confermati con PUT /messages
# - Messaggi salvati in Firestore
```

**Verifica:**
- [ ] Messaggio da Reservation 1 recuperato correttamente
- [ ] `message_id`, `reservation_id`, `property_id` estratti correttamente
- [ ] Messaggio salvato in Firestore conversations
- [ ] Messaggi confermati e rimossi dalla coda

#### **Step 3: Testa Invio Risposte**

```bash
# Dopo che un messaggio è stato processato, verifica:
# - GeminiService ha generato risposta
# - BookingReplyService ha inviato risposta via API
```

**Verifica:**
- [ ] Risposta inviata via `POST /properties/{property_id}/conversations/{conversation_id}`
- [ ] Risposta visibile nell'app Booking.com come guest
- [ ] `message_id` della risposta salvato in Firestore
- [ ] Opzionale: messaggio marcato come letto (`PUT /tags/message_read`)

#### **Step 4: Testa Property Inizia Conversazione (Reservation 2)**

1. Recupera conversation_id per Reservation 2:
   ```bash
   GET /properties/{property_id}/conversations/type/reservation?conversation_reference={reservation_id}
   ```

2. Invia messaggio come property:
   ```bash
   POST /properties/{property_id}/conversations/{conversation_id}
   {
     "message": {
       "content": "Benvenuto! Come possiamo aiutarti?"
     }
   }
   ```

3. Verifica che il messaggio arrivi al guest via email/app

#### **Step 5: Self-Service Requests (Opzionale - v1.2)**

Se hai abilitato `enable_self_services_messaging`:

1. Crea nuova test reservation (Reservation A)
2. Come guest, durante booking o dopo, includi orario arrivo stimato
3. Invia messaggio free-text come guest
4. Verifica che arrivi self-service request "Check-in time" via API
5. Rispondi via API (priorità prima delle risposte normali)
6. Verifica che self-service request sia marcata come risposta

---

### **Testing Reservation API**

#### **Step 1: Crea Test Reservation**

1. Vai a: `https://secure.booking.com/book.html?test=1;hotel_id={property_id}`
2. Crea una prenotazione completa con:
   - Carta di credito test: `4111111111111111`
   - Guest info completa (nome, email, telefono)
   - Date check-in/check-out
   - Room type e rate plan

#### **Step 2: Testa Polling Prenotazioni**

```bash
# Avvia il polling service
python -m email_agent_service.services.booking_reservation_polling_service

# Verifica nei log:
# - GET /OTA_HotelResNotif chiamato ogni 20 secondi
# - XML response ricevuto
# - Prenotazioni parsate correttamente
```

**Verifica:**
- [ ] GET /OTA_HotelResNotif restituisce la nuova prenotazione
- [ ] XML parsato correttamente
- [ ] Dati estratti: `reservation_id`, `property_id`, `guest_name`, `guest_email`, dates, totals
- [ ] Prenotazione salvata in Firestore `reservations` collection
- [ ] Client creato/aggiornato in Firestore `clients` collection
- [ ] POST /OTA_HotelResNotif acknowledgement inviato con successo

#### **Step 3: Testa Modifiche e Cancellazioni**

1. Modifica la test reservation dall'Extranet Booking.com (cambia date o ospiti)
2. Verifica che polling service recuperi la modifica via `GET /OTA_HotelResModifyNotif`
3. Verifica che modifica sia applicata in Firestore
4. Cancella la test reservation dall'Extranet
5. Verifica che cancellazione sia recuperata e applicata

---

### **Checklist Testing Completo**

#### **Messaging API:**
- [ ] ✅ Recupero messaggi da `/messages/latest`
- [ ] ✅ Conferma messaggi con `PUT /messages`
- [ ] ✅ Invio risposta via `POST /conversations/{id}`
- [ ] ✅ Recupero conversation_id da reservation_id
- [ ] ✅ Property inizia conversazione
- [ ] ✅ Guest riceve risposta
- [ ] ✅ Messaggi marcati come letti (opzionale)
- [ ] ✅ Deduplicazione messaggi (no duplicati)

#### **Reservation API:**
- [ ] ✅ Recupero nuove prenotazioni (`GET /OTA_HotelResNotif`)
- [ ] ✅ Acknowledgement prenotazioni (`POST /OTA_HotelResNotif`)
- [ ] ✅ Recupero modifiche (`GET /OTA_HotelResModifyNotif`)
- [ ] ✅ Acknowledgement modifiche (`POST /OTA_HotelResModifyNotif`)
- [ ] ✅ Parsing XML OTA corretto
- [ ] ✅ Salvataggio in Firestore corretto
- [ ] ✅ Creazione/aggiornamento client automatico
- [ ] ✅ Polling ogni 20 secondi funzionante

#### **Integrazione End-to-End:**
- [ ] ✅ Prenotazione creata → Import automatico → Disponibile in sistema
- [ ] ✅ Messaggio guest → Polling → Gemini risposta → Invio risposta
- [ ] ✅ Nessuna duplicazione prenotazioni/messaggi
- [ ] ✅ Error handling corretto (401, 403, 429, 500)
- [ ] ✅ Rate limiting gestito correttamente

---

### **Tools e Utilities per Testing**

1. **cURL/Postman** per testare API direttamente:
   ```bash
   # Test autenticazione
   curl -X GET "https://supply-xml.booking.com/messaging/messages/latest" \
     -u "username:password" \
     -H "Accept-Version: 1.2"
   
   # Test invio messaggio
   curl -X POST "https://supply-xml.booking.com/messaging/properties/{property_id}/conversations/{conversation_id}" \
     -u "username:password" \
     -H "Content-Type: application/json" \
     -d '{"message": {"content": "Test message"}}'
   ```

2. **Logging dettagliato** durante sviluppo:
   - Log tutte le chiamate API (request/response)
   - Log RUID (Request Unique ID) per supporto Booking.com
   - Log errori con dettagli completi

3. **Firestore Console** per verificare dati:
   - Verifica prenotazioni salvate
   - Verifica messaggi salvati in conversations
   - Verifica client creati/aggiornati

---

### **Certificazione Booking.com (Opzionale)**

Se vuoi passare la certificazione ufficiale Booking.com:

1. Completa il self-assessment tutorial per Messaging API
2. Documenta tutti i RUID delle operazioni
3. Screenshot del sistema funzionante
4. Invia email a Connectivity Support con:
   - Provider ID
   - Proof completato (RUIDs + screenshots)

---

## ✅ Conclusione

**La documentazione è completa e sufficiente per implementare l'integrazione.**

**Prossimi passi:**
1. Ottenere credenziali Machine Account Booking.com
2. Verificare accesso Provider Portal
3. Iniziare Fase 1: Setup e Client API Base
4. Testare con property di test seguendo la guida sopra

**Tempo stimato totale: 25-32 giorni lavorativi**

