# 📋 Piano di Sviluppo Ordinato - Integrazione Booking.com API

**Obiettivo:** Import automatico prenotazioni + Risposta automatica messaggi  
**Data creazione:** 2025-01-15  
**Versione:** 1.0

---

## 🎯 Overview

Questo documento fornisce un piano di sviluppo step-by-step, ordinato e sequenziale per implementare l'integrazione Booking.com API.

**IMPORTANTE: Il servizio è MULTI-HOST by design!**
- Una sola Machine Account Booking.com (condivisa)
- Gestisce TUTTI gli host contemporaneamente
- Mapping `booking_property_id` → `host_id` necessario

**Due flussi paralleli:**
1. **Reservation API** → Import automatico prenotazioni (può essere sviluppato in parallelo)
2. **Messaging API** → Risposta automatica messaggi (può essere sviluppato in parallelo)

**Vedi anche:** `GESTIONE_MULTI_HOST.md` per dettagli architettura multi-host

---

## 📊 Roadmap Generale

```
FASE 0: Setup Preliminare (1-2 giorni)
    ↓
FASE 1: Client API Base (4-5 giorni)
    ↓
FASE 2A: Import Prenotazioni ─┐
    (5-6 giorni)                │
                                 ├──> FASE 4: Testing Integrato (4-5 giorni)
FASE 2B: Messaging ─────────────┘
    (4-5 giorni)
    ↓
FASE 3: Integrazione End-to-End (3-4 giorni)
    ↓
FASE 4: Testing e Refinement (4-5 giorni)
    ↓
FASE 5: Deployment (2 giorni)

TOTALE: 25-32 giorni lavorativi
```

---

## 🚀 FASE 0: Setup Preliminare (1-2 giorni)

**Obiettivo:** Preparare ambiente e credenziali

### Task List

- [ ] **T0.1** Ottenere credenziali Machine Account Booking.com
  - Contattare Booking.com Connectivity Support
  - Richiedere username e password Machine Account
  - Verificare Provider ID

- [ ] **T0.2** Accesso Provider Portal
  - Login su Provider Portal Booking.com
  - Verificare lista properties disponibili
  - Identificare property ID di test

- [ ] **T0.3** Configurazione Provider Portal
  - Abilitare accesso a `/messages/latest` endpoint (Messaging API)
  - Verificare accesso a Reservation API endpoints
  - (Opzionale) Abilitare feature `enable_self_services_messaging`

- [ ] **T0.4** Setup Ambiente Locale
  - Verificare Python 3.9+ installato
  - Setup virtual environment se necessario
  - Verificare accesso a Firestore

- [ ] **T0.5** Documentazione Setup
  - Documentare credenziali in Secret Manager (non in codice!)
  - Creare file `.env.example` con variabili necessarie
  - Documentare property IDs per testing

**Deliverable:**
- ✅ Credenziali configurate e verificate
- ✅ Provider Portal accessibile
- ✅ Property di test identificata
- ✅ Ambiente locale pronto

---

## 🔧 FASE 1: Client API Base (4-5 giorni)

**Obiettivo:** Creare client API per Booking.com (Reservation + Messaging)

### Task List

#### **Giorno 1-2: Configurazione e Setup Base**

- [ ] **T1.1** Aggiungere configurazione in `config/settings.py`
  ```python
  # Aggiungere classe Settings:
  class BookingSettings:
      MESSAGING_API_BASE_URL: str = "https://supply-xml.booking.com/messaging"
      RESERVATION_API_BASE_URL: str = "https://secure-supply-xml.booking.com/hotels/ota/"
      API_VERSION: str = "1.2"
      USERNAME: str  # da env var
      PASSWORD: str  # da env var
      POLLING_INTERVAL_RESERVATIONS: int = 20  # secondi
      POLLING_INTERVAL_MESSAGES: int = 60  # secondi
  ```

- [ ] **T1.2** Aggiungere variabili ambiente
  - `BOOKING_API_USERNAME`
  - `BOOKING_API_PASSWORD`
  - Aggiornare `.env.example`

- [ ] **T1.3** Creare struttura directory
  ```
  src/email_agent_service/
    services/
      integrations/
        __init__.py
        booking_messaging_client.py  (NUOVO)
        booking_reservation_client.py  (NUOVO)
    models/
      booking_message.py  (NUOVO)
      booking_reservation.py  (NUOVO)
    parsers/
      booking_reservation_parser.py  (NUOVO)
  ```

#### **Giorno 2-3: Messaging Client**

- [ ] **T1.4** Creare `booking_messaging_client.py`
  ```python
  class BookingMessagingClient:
      def __init__(self, username: str, password: str, base_url: str)
      def authenticate() -> requests.auth.HTTPBasicAuth
      def _request(method, endpoint, **kwargs) -> requests.Response
      def get_latest_messages() -> dict
      def confirm_messages(number_of_messages: int) -> dict
      def get_conversations(property_id: str, page_id: str = None) -> dict
      def get_conversation_by_id(property_id: str, conversation_id: str) -> dict
      def get_conversation_by_reservation(property_id: str, reservation_id: str) -> dict
      def send_message(property_id: str, conversation_id: str, content: str, attachment_ids: List[str] = None) -> dict
      def mark_as_read(property_id: str, conversation_id: str, message_ids: List[str], participant_id: str) -> dict
  ```
  - Implementare Basic Auth
  - Implementare `_request()` con retry logic e error handling
  - Gestire rate limiting (429) con exponential backoff
  - Aggiungere header `Accept-Version: 1.2`
  - Gestire errori 401, 403, 429, 500

- [ ] **T1.5** Test manuale Messaging Client
  - Test autenticazione con cURL/Postman
  - Test `get_latest_messages()` (dovrebbe restituire vuoto se nessun messaggio)
  - Verificare formato response

#### **Giorno 3-4: Reservation Client**

- [ ] **T1.6** Creare `booking_reservation_client.py`
  ```python
  class BookingReservationClient:
      def __init__(self, username: str, password: str, base_url: str)
      def authenticate() -> requests.auth.HTTPBasicAuth
      def _request(method, endpoint, **kwargs) -> requests.Response
      def get_new_reservations(hotel_ids: str = None, last_change: str = None, limit: int = None) -> str  # XML
      def acknowledge_new_reservations(reservations_xml: str) -> str  # XML
      def get_modified_reservations(hotel_ids: str = None, last_change: str = None, limit: int = None) -> str  # XML
      def acknowledge_modified_reservations(reservations_xml: str) -> str  # XML
  ```
  - Implementare Basic Auth (stesso formato Messaging)
  - Gestire XML responses (non JSON)
  - Gestire errori comuni

- [ ] **T1.7** Test manuale Reservation Client
  - Test `get_new_reservations()` (dovrebbe restituire XML vuoto se nessuna prenotazione)
  - Verificare formato XML response

#### **Giorno 4-5: Modelli Dati**

- [ ] **T1.8** Creare `models/booking_message.py`
  ```python
  @dataclass
  class BookingMessage:
      message_id: str
      content: str
      timestamp: datetime
      sender: BookingSender
      conversation: BookingConversation
      message_type: Optional[str] = None
      attachment_ids: List[str] = field(default_factory=list)
      
  @dataclass
  class BookingSender:
      participant_id: str
      participant_type: str  # "GUEST" o "property"
      name: Optional[str] = None
      
  @dataclass
  class BookingConversation:
      conversation_id: str
      conversation_type: str  # "reservation" o "request_to_book"
      conversation_reference: str  # reservation_id
      property_id: Optional[str] = None
      
  def booking_message_from_api_response(response_data: dict) -> BookingMessage
  def booking_message_to_internal_format(booking_msg: BookingMessage) -> dict
  ```

- [ ] **T1.9** Creare `models/booking_reservation.py`
  ```python
  @dataclass
  class BookingReservation:
      reservation_id: str
      property_id: str
      check_in: datetime
      check_out: datetime
      guest_name: str
      guest_email: str
      guest_phone: Optional[str] = None
      adults: int
      children: int = 0
      total_amount: float
      currency: str
      # ... altri campi
      
  def booking_reservation_from_xml(xml_string: str) -> List[BookingReservation]
  def booking_reservation_to_firestore_format(booking_res: BookingReservation) -> dict
  ```

**Deliverable:**
- ✅ Client API funzionanti (Messaging + Reservation)
- ✅ Modelli dati definiti
- ✅ Test manuali base superati
- ✅ Error handling implementato

---

## 📥 FASE 2A: Import Automatico Prenotazioni (5-6 giorni)

**Obiettivo:** Polling prenotazioni → Parse XML → Salva in Firestore

### Task List

#### **Giorno 1-2: Parser XML OTA**

- [ ] **T2A.1** Creare `parsers/booking_reservation_parser.py`
  ```python
  class BookingReservationParser:
      def parse_ota_xml(xml_string: str) -> List[BookingReservation]
      def _extract_reservation_id(xml_element) -> str
      def _extract_property_id(xml_element) -> str
      def _extract_dates(xml_element) -> Tuple[datetime, datetime]
      def _extract_guest_info(xml_element) -> dict
      def _extract_totals(xml_element) -> dict
      def _extract_payment_info(xml_element) -> dict  # VCC, etc.
  ```
  - Usare `xml.etree.ElementTree` o `lxml`
  - Parsare struttura XML OTA (vedi documentazione)
  - Gestire multi-room reservations
  - Gestire modifiche e cancellazioni

- [ ] **T2A.2** Test Parser con XML di esempio
  - Creare file test XML con struttura OTA
  - Verificare estrazione corretta di tutti i campi
  - Test edge cases (multi-room, senza phone, etc.)

#### **Giorno 2-3: Polling Service**

- [ ] **T2A.3** Creare `services/booking_reservation_polling_service.py` - **MULTI-HOST**
  ```python
  class BookingReservationPollingService:
      def __init__(
          self,
          client: BookingReservationClient,  # Credenziali condivise per tutti gli host
          persistence_service: PersistenceService,
          firestore_client: firestore.Client,  # Per mapping repository
          polling_interval: int = 20
      )
      def start() -> None  # Avvia thread in background
      def stop() -> None  # Ferma thread
      def _poll_loop() -> None  # background thread
      def _find_host_id_for_property(booking_property_id: str) -> Optional[str]  # Mapping property → host
      def _poll_new_reservations() -> None  # Poll e mappa per host
  ```
  - **IMPORTANTE: MULTI-HOST**
    - Usa UN SOLO set di credenziali Booking.com (Machine Account condiviso)
    - Recupera prenotazioni per TUTTE le properties del provider
    - Mappa ogni prenotazione al corretto host_id usando `booking_property_id`
  - Implementare polling ogni 20 secondi
  - Gestire eccezioni (non fermare loop su errore)
  - Attesa 5 secondi tra POST acknowledgement e successivo GET
  - Log warning per prenotazioni senza mapping (verranno saltate)

- [ ] **T2A.4** Test Polling Service
  - Avviare service in background
  - Creare test reservation su Booking.com
  - Verificare che venga recuperata entro 20-40 secondi

#### **Giorno 3-4: Persistence Service**

- [ ] **T2A.5** Estendere `services/persistence_service.py` - **MULTI-HOST**
  ```python
  def save_booking_reservation(
      reservation: BookingReservation,
      host_id: str,  # Già mappato dal polling service
  ) -> None:
      # 1. host_id è già determinato dal polling service (via mapping)
      # 2. Cerca/crea client usando guest_email + host_id
      # 3. Cerca/crea property usando booking_property_id + host_id
      #    - Se non esiste, crea nuova property con requiresReview=True
      # 4. Salva reservation in Firestore con host_id corretto
      # 5. Collega reservation a client e property
  ```
  - **Nota:** Il polling service ha già fatto il mapping `booking_property_id` → `host_id`
  - Persistence service riceve `host_id` già corretto

- [ ] **T2A.6** Implementare mapping property_id Booking.com → host_id **CRITICO MULTI-HOST**
  - [x] Creare `repositories/booking_property_mappings.py` ✅
  - [x] Repository per mapping `booking_property_id` → `host_id` ✅
  - [ ] Tabella Firestore: `bookingPropertyMappings/{id}`
    - `bookingPropertyId`: Property ID Booking.com (es: "8011855")
    - `hostId`: ID host proprietario
    - `internalPropertyId`: Property ID interno (opzionale, può essere mappato dopo)
    - `propertyName`: Nome property (opzionale, per reference)
  - [ ] API endpoint per gestire mapping (creare/aggiornare/eliminare)
  - [ ] Script per inizializzare mapping iniziali
  - **Importante:** Senza mapping, le prenotazioni vengono saltate (log warning)

- [ ] **T2A.7** Test Persistence
  - Test salvataggio prenotazione
  - Test creazione client automatica
  - Test aggiornamento reservation esistente
  - Verificare dati in Firestore Console

#### **Giorno 4-5: Integrazione Completa**

- [ ] **T2A.8** Collegare Polling → Parser → Persistence - **MULTI-HOST**
  ```python
  # In booking_reservation_polling_service.py
  def _poll_new_reservations():
      xml_response = client.get_new_reservations()  # Recupera TUTTE le prenotazioni
      reservations = parse_ota_xml(xml_response)
      for res in reservations:
          # Trova host_id usando mapping
          host_id = _find_host_id_for_property(res.property_id)
          if host_id:
              persistence_service.save_booking_reservation(res, host_id)
      acknowledge_reservations(xml_response)
  ```
  - **IMPORTANTE:** Ogni prenotazione viene mappata al corretto host_id prima del salvataggio

- [ ] **T2A.9** Gestire modifiche e cancellazioni
  - Poll `get_modified_reservations()` ogni 20s
  - Distinguere modifiche vs cancellazioni
  - Aggiornare reservation in Firestore
  - Per cancellazioni: aggiornare status a "cancelled"

- [ ] **T2A.10** Test End-to-End Import
  - Creare test reservation
  - Verificare import entro 20-40s
  - Modificare reservation
  - Verificare aggiornamento
  - Cancellare reservation
  - Verificare status "cancelled"

**Deliverable:**
- ✅ Polling service funzionante
- ✅ Parser XML completo
- ✅ Persistence in Firestore
- ✅ Test end-to-end superati

---

## 💬 FASE 2B: Messaging API - Risposta Automatica (4-5 giorni)

**Obiettivo:** Polling messaggi → Processa → Gemini → Invia risposta

### Task List

#### **Giorno 1: Polling Service**

- [ ] **T2B.1** Creare `services/booking_message_polling_service.py`
  ```python
  class BookingMessagePollingService:
      def __init__(self, client: BookingMessagingClient, processor: BookingMessageProcessor)
      def start_polling(interval: int = 60) -> None
      def poll_messages() -> List[BookingMessage]
      def confirm_messages(number_of_messages: int) -> None
      def _poll_loop() -> None
  ```
  - Polling ogni 30-60 secondi
  - Gestire deduplicazione (usare `processed_message_ids` in Firestore)
  - Gestire errori senza fermare loop

- [ ] **T2B.2** Test Polling
  - Avviare service
  - Creare test message come guest
  - Verificare recupero entro 60s

#### **Giorno 1-2: Message Processor**

- [ ] **T2B.3** Creare `services/booking_message_processor.py`
  ```python
  class BookingMessageProcessor:
      def process_message(booking_message: BookingMessage) -> ParsedMessage:
          # 1. Filtra solo messaggi guest (participant_type: "GUEST")
          # 2. Ignora automatically_sent_template (opzionale)
          # 3. Estrae reservation_id, property_id, guest_name
          # 4. Converte in formato interno (compatibile con GuestMessagePipeline)
  ```
  - Convertire `BookingMessage` → formato compatibile con `GuestMessageInfo`
  - Filtrare messaggi non guest
  - Gestire self-service requests (v1.2)

- [ ] **T2B.4** Test Processor
  - Test conversione formato
  - Test filtri
  - Test estrazione dati

#### **Giorno 2-3: Estendere GuestMessagePipeline**

- [ ] **T2B.5** Modificare `services/guest_message_pipeline.py`
  ```python
  # Aggiungere supporto per source="booking_api"
  def should_process_message(parsed_email: ParsedEmail, source: str = "email") -> tuple:
      # Se source="booking_api", usa formato Booking invece di email
      
  def extract_context(parsed_email: ParsedEmail, source: str = "email") -> GuestMessageContext:
      # Per Booking API, reservation_id viene da conversation_reference
      # Non serve cercare per thread_id come Airbnb
  ```

- [ ] **T2B.6** Test Pipeline con formato Booking
  - Test `should_process_message()` con dati Booking
  - Test `extract_context()` con reservation_id Booking
  - Verificare recupero reservation da Firestore

#### **Giorno 3-4: Reply Service**

- [ ] **T2B.7** Creare `services/booking_reply_service.py`
  ```python
  class BookingReplyService:
      def __init__(self, client: BookingMessagingClient)
      def send_reply(
          property_id: str,
          reservation_id: str,
          message_content: str,
          mark_as_read: bool = True
      ) -> str:  # message_id
          # 1. Recupera conversation_id da reservation_id
          # 2. Invia messaggio via API
          # 3. (Opzionale) Marca messaggio come letto
  ```
  - Implementare recupero `conversation_id` da `reservation_id`
  - Implementare invio messaggio
  - Gestire errori (403 property access, etc.)

- [ ] **T2B.8** Test Reply Service
  - Test invio messaggio
  - Verificare messaggio arriva al guest
  - Test mark as read

#### **Giorno 4-5: Integrazione End-to-End Messaging**

- [ ] **T2B.9** Collegare tutto il flow
  ```python
  # In app.py o route handler
  # 1. BookingMessagePollingService.poll_messages()
  # 2. BookingMessageProcessor.process_message()
  # 3. GuestMessagePipelineService.should_process_message()
  # 4. GuestMessagePipelineService.extract_context()
  # 5. GeminiService.generate_reply()
  # 6. BookingReplyService.send_reply()
  ```

- [ ] **T2B.10** Test End-to-End Messaging
  - Creare test reservation
  - Inviare messaggio come guest
  - Verificare:
    - Messaggio recuperato
    - Risposta AI generata
    - Risposta inviata via API
    - Guest riceve risposta

**Deliverable:**
- ✅ Polling messaggi funzionante
- ✅ Processamento messaggi
- ✅ Invio risposte via API
- ✅ Test end-to-end superati

---

## 🔗 FASE 3: Integrazione End-to-End (3-4 giorni)

**Obiettivo:** Collegare tutti i componenti e testare flusso completo

### Task List

- [ ] **T3.1** Avviare entrambi i polling service - **MULTI-HOST**
  - Reservation polling ogni 20s (gestisce TUTTI gli host)
  - Message polling ogni 60s (gestisce TUTTI gli host)
  - Verificare coesistenza senza conflitti
  - Verificare che mapping `booking_property_id` → `host_id` funzioni correttamente
  - Test con più host contemporaneamente

- [ ] **T3.2** Test Flusso Completo
  1. Creare test reservation → Verificare import
  2. Guest invia messaggio → Verificare risposta AI
  3. Modificare reservation → Verificare aggiornamento
  4. Cancellare reservation → Verificare status

- [ ] **T3.3** Gestire edge cases
  - Messaggio ricevuto prima che reservation sia importata
  - Duplicazione messaggi/prenotazioni
  - Errori temporanei API
  - Rate limiting

- [ ] **T3.4** Logging e Monitoring
  - Log strutturato per tutti gli eventi
  - Metriche: prenotazioni importate, messaggi processati, risposte inviate
  - Alert su errori continui

- [ ] **T3.5** Documentazione codice
  - Docstrings per tutte le classi/funzioni
  - README aggiornato
  - Commenti su decisioni architetturali

**Deliverable:**
- ✅ Sistema integrato funzionante
- ✅ Edge cases gestiti
- ✅ Logging completo
- ✅ Documentazione aggiornata

---

## 🧪 FASE 4: Testing e Refinement (4-5 giorni)

**Obiettivo:** Test completi, bug fixing, ottimizzazioni

### Task List

- [ ] **T4.1** Unit Tests
  - Test `BookingMessagingClient` (mock responses)
  - Test `BookingReservationClient` (mock XML)
  - Test `BookingMessageProcessor`
  - Test `BookingReservationParser`
  - Test `BookingReplyService`

- [ ] **T4.2** Integration Tests
  - Test con Booking.com test environment
  - Test polling → processamento → risposta
  - Test deduplicazione
  - Test error handling

- [ ] **T4.3** Stress Testing
  - Test con molte prenotazioni simultanee
  - Test con molti messaggi simultanei
  - Verificare performance e stabilità

- [ ] **T4.4** Bug Fixing
  - Risolvere bug trovati durante testing
  - Ottimizzare performance
  - Migliorare error messages

- [ ] **T4.5** Refinement
  - Code review
  - Refactoring se necessario
  - Ottimizzazioni finali

**Deliverable:**
- ✅ Test coverage adeguato
- ✅ Bug risolti
- ✅ Performance ottimizzate
- ✅ Code review completato

---

## 🚀 FASE 5: Deployment (2 giorni)

**Obiettivo:** Preparare per produzione

### Task List

- [ ] **T5.1** Configurazione Produzione
  - Variabili ambiente produzione
  - Secret Manager per credenziali
  - Configurazione polling intervals

- [ ] **T5.2** Monitoring Setup
  - Logging in Cloud Logging
  - Metriche in Cloud Monitoring
  - Alert configurazione

- [ ] **T5.3** Documentazione Finale
  - README completo
  - Troubleshooting guide
  - Runbook per operations

- [ ] **T5.4** Deploy Staging
  - Deploy su ambiente staging
  - Test finale su staging
  - Verifica monitoring

- [ ] **T5.5** Deploy Produzione
  - Deploy su produzione
  - Monitoraggio iniziale
  - Verifica funzionamento

**Deliverable:**
- ✅ Sistema in produzione
- ✅ Monitoring attivo
- ✅ Documentazione completa

---

## 📝 Checklist Progresso

### Fase 0: Setup Preliminare
- [ ] Credenziali ottenute
- [ ] Provider Portal accessibile
- [ ] Property test identificata
- [ ] Ambiente locale pronto

### Fase 1: Client API Base
- [ ] Configurazione settings
- [ ] BookingMessagingClient
- [ ] BookingReservationClient
- [ ] Modelli dati
- [ ] Test manuali base

### Fase 2A: Import Prenotazioni
- [ ] Parser XML
- [ ] Polling service
- [ ] Persistence service
- [ ] Test end-to-end

### Fase 2B: Messaging
- [ ] Polling service
- [ ] Message processor
- [ ] Reply service
- [ ] Test end-to-end

### Fase 3: Integrazione
- [ ] Flusso completo funzionante
- [ ] Edge cases gestiti
- [ ] Logging completo

### Fase 4: Testing
- [ ] Unit tests
- [ ] Integration tests
- [ ] Bug fixing
- [ ] Refinement

### Fase 5: Deployment
- [ ] Configurazione produzione
- [ ] Monitoring
- [ ] Deploy completato

---

## 🎯 Priorità e Dipendenze

**Ordine consigliato (sequenziale):**
1. **Fase 0** → **Fase 1** (obbligatorio, base per tutto)
2. **Fase 2A** e **Fase 2B** possono essere sviluppati **in parallelo** (diversi sviluppatori)
3. **Fase 3** richiede completamento di **Fase 2A + 2B**
4. **Fase 4** richiede completamento di **Fase 3**
5. **Fase 5** richiede completamento di **Fase 4**

**Task critici (bloccanti):**
- T0.1, T0.2: Credenziali (blocca tutto)
- T1.4, T1.6: Client API (blocca Fase 2A e 2B)
- T2A.3, T2B.1: Polling services (blocca integrazione)

---

## 📚 Riferimenti Utili

Durante lo sviluppo, consultare:
- `ANALISI_INTEGRAZIONE_BOOKING_API.md` - Analisi completa e documentazione
- `api_doc_booking/messaging_api/` - Documentazione Messaging API
- `api_doc_booking/reservation_api/` - Documentazione Reservation API
- Codice esistente Airbnb per pattern simili

---

---

## 🚦 Cosa si può sviluppare PRIMA di avere le credenziali?

**✅ SÌ, puoi iniziare a sviluppare SUBITO senza credenziali!**

### **Cosa si può fare SENZA credenziali (80% del lavoro):**

#### **1. Struttura Codice e Configurazione**
- [x] **T1.1** Configurazione in `settings.py` (puoi usare placeholder)
- [x] **T1.2** Struttura directory e file
- [x] **T1.4-T1.6** Client API con **mock responses** per sviluppo

#### **2. Client API con Mock**
- [x] **T1.4** `BookingMessagingClient` con metodi che usano `requests_mock` o `unittest.mock`
  ```python
  # Esempio: Client con mock per sviluppo
  from unittest.mock import Mock, patch
  
  class BookingMessagingClient:
      def __init__(self, username=None, password=None, mock_mode=True):
          self.mock_mode = mock_mode
          if mock_mode:
              # Usa mock responses invece di chiamate reali
              
      def get_latest_messages(self):
          if self.mock_mode:
              return self._mock_get_latest_messages()
          # Chiamata reale...
  ```

#### **3. Modelli Dati**
- [x] **T1.8-T1.9** Tutti i modelli dati (non richiedono API)
- [x] Funzioni di conversione formati

#### **4. Parser XML (se hai esempio XML)**
- [x] **T2A.1** `BookingReservationParser` usando XML di esempio dalla documentazione
  - Puoi creare file test XML basato sulla documentazione OTA
  - Testare parsing senza chiamare API

#### **5. Business Logic**
- [x] **T2A.3** Polling Service (con mock client)
- [x] **T2B.3** Message Processor
- [x] **T2B.5** Estensioni GuestMessagePipeline

#### **6. Persistence Service**
- [x] **T2A.5** Salvataggio in Firestore (non richiede Booking API)
- [x] Logica di mapping property_id

#### **7. Unit Tests**
- [x] **T4.1** Tutti gli unit tests (con mock)
- [x] Test parsing, conversioni, business logic

### **Cosa RICHIEDE credenziali reali:**

#### **⚠️ Necessario avere credenziali per:**

1. **Test Integration Real**
   - [ ] **T4.2** Test con Booking.com API reali
   - [ ] **T3.2** Test flusso end-to-end completo
   - [ ] Verifica autenticazione funzionante

2. **Verifica Format Response**
   - [ ] Verificare formato esatto delle risposte API
   - [ ] Testare edge cases reali

3. **Testing con Test Reservations**
   - [ ] Creare test reservations reali
   - [ ] Testare polling con dati reali
   - [ ] Verificare import prenotazioni

4. **Certificazione Booking.com**
   - [ ] Self-assessment tutorial (richiede credenziali)

---

## 💡 Strategia di Sviluppo Consigliata

### **Opzione A: Sviluppo con Mock (Consigliato)**

**Inizia SUBITO anche senza credenziali:**

1. **Settimana 1-2: Sviluppo con Mock**
   - Implementare T1.1-T1.9 (config, client con mock, modelli)
   - Implementare T2A.1-T2A.5 (parser, polling, persistence) con mock
   - Implementare T2B.1-T2B.6 (messaging) con mock
   - Scrivere unit tests completi

2. **Nel frattempo: Richiedere Credenziali**
   - In parallelo, contattare Booking.com Connectivity Support
   - Richiedere Machine Account
   - Attendere approvazione (può richiedere giorni/settimane)

3. **Settimana 3+: Integrazione Reale**
   - Quando arrivano credenziali, sostituire mock con chiamate reali
   - Test integration reali
   - Verifica e bug fixing

### **Opzione B: Attendere Credenziali**

- Aspettare di avere credenziali prima di iniziare
- ⚠️ **Svantaggio:** Perdi tempo mentre attendi (può richiedere settimane)

---

## 🛠️ Esempio: Client con Mock Mode

```python
# services/integrations/booking_messaging_client.py

from typing import Optional
import requests
from unittest.mock import Mock

class BookingMessagingClient:
    def __init__(
        self, 
        username: Optional[str] = None, 
        password: Optional[str] = None,
        base_url: str = "https://supply-xml.booking.com/messaging",
        mock_mode: bool = False
    ):
        self.username = username
        self.password = password
        self.base_url = base_url
        self.mock_mode = mock_mode or not (username and password)
        
        if self.mock_mode:
            self._init_mock_responses()
    
    def _init_mock_responses(self):
        """Inizializza mock responses per sviluppo senza credenziali"""
        self._mock_responses = {
            'messages_latest': {
                "data": {
                    "messages": [
                        {
                            "message_id": "test-msg-123",
                            "content": "Test message from guest",
                            "sender": {
                                "participant_id": "guest-123",
                                "metadata": {
                                    "participant_type": "GUEST",
                                    "name": "Test Guest"
                                }
                            },
                            "conversation": {
                                "conversation_id": "conv-123",
                                "conversation_type": "reservation",
                                "conversation_reference": "9876543210"  # reservation_id
                            },
                            "timestamp": "2025-01-15T10:00:00Z",
                            "message_type": "free_text"
                        }
                    ],
                    "ok": True,
                    "number_of_messages": 1
                }
            }
        }
    
    def get_latest_messages(self):
        if self.mock_mode:
            logger.info("[MOCK MODE] Returning mock messages")
            return self._mock_responses['messages_latest']
        
        # Chiamata reale API
        response = self._request('GET', '/messages/latest')
        return response.json()
    
    def _request(self, method: str, endpoint: str, **kwargs):
        if self.mock_mode:
            # Ritorna mock response
            return MockResponse(self._get_mock_for_endpoint(endpoint))
        
        # Chiamata HTTP reale
        auth = requests.auth.HTTPBasicAuth(self.username, self.password)
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Accept-Version": "1.2",
            **kwargs.get('headers', {})
        }
        return requests.request(method, url, auth=auth, headers=headers, **kwargs)
```

### **File Mock Responses di Esempio**

Crea `tests/fixtures/booking_api_responses.py`:

```python
# Test fixtures con response reali dalla documentazione

MOCK_MESSAGES_LATEST_RESPONSE = {
    "meta": {"ruid": "test-ruid-123"},
    "warnings": [],
    "data": {
        "messages": [
            {
                "message_id": "4ad42260-e0aa-11ea-b1cb-0975761ce091",
                "message_type": "free_text",
                "content": "Test guest message",
                "timestamp": "2020-08-17T16:54:19.270Z",
                "sender": {
                    "participant_id": "9f6be5fd-b3a8-5691-9cf9-9ab6c6217327",
                    "metadata": {
                        "participant_type": "GUEST",
                        "name": "Test Guest"
                    }
                },
                "conversation": {
                    "conversation_type": "reservation",
                    "conversation_id": "f3a9c29d-480d-5f5b-a6c0-65451e335353",
                    "conversation_reference": "3812391309"
                },
                "attachment_ids": []
            }
        ],
        "ok": True,
        "number_of_messages": 1,
        "timestamp": "2020-08-18T14:59:26.41"
    },
    "errors": []
}

MOCK_OTA_XML_RESPONSE = """<?xml version="1.0" encoding="UTF-8"?>
<OTA_HotelResNotifRQ xmlns="http://www.opentravel.org/OTA/2003/05">
    <HotelReservations>
        <HotelReservation>
            <RoomStays>
                <RoomStay IndexNumber="460">
                    <BasicPropertyInfo HotelCode="12963644"/>
                    <RoomRate EffectiveDate="2025-03-29">
                        <Rates>
                            <Rate>
                                <Total AmountBeforeTax="500" CurrencyCode="EUR" DecimalPlaces="2"/>
                            </Rate>
                        </Rates>
                    </RoomRate>
                </RoomStay>
            </RoomStays>
            <ResGlobalInfo>
                <HotelReservationIDs>
                    <HotelReservationID ResID_Value="4705950059" ResID_Date="2025-03-10T10:33:37"/>
                </HotelReservationIDs>
                <Profiles>
                    <ProfileInfo>
                        <Profile>
                            <Customer>
                                <PersonName>
                                    <GivenName>Test</GivenName>
                                    <Surname>Guest</Surname>
                                </PersonName>
                                <Telephone PhoneNumber="+39 333 1234567"/>
                                <Email>test.guest@example.com</Email>
                            </Customer>
                        </Profile>
                    </ProfileInfo>
                </Profiles>
                <Total AmountBeforeTax="500" CurrencyCode="EUR" DecimalPlaces="2"/>
            </ResGlobalInfo>
        </HotelReservation>
    </HotelReservations>
</OTA_HotelResNotifRQ>"""
```

---

## 📋 Task da Iniziare SUBITO (senza credenziali)

### **Priorità Alta (puoi iniziare oggi):**

1. ✅ **T1.1** Configurazione settings (placeholder per credenziali)
2. ✅ **T1.2** Struttura directory e file
3. ✅ **T1.8** Modelli dati `booking_message.py`
4. ✅ **T1.9** Modelli dati `booking_reservation.py`
5. ✅ **T1.4** Client Messaging con mock mode
6. ✅ **T1.6** Client Reservation con mock mode
7. ✅ **T2A.1** Parser XML con XML di esempio
8. ✅ **T2B.3** Message Processor

### **Inizia in parallelo:**
- Richiedere credenziali Booking.com (T0.1)

---

---

## 🧪 Test: Automatizzati vs Manuali

### **📖 Documentazione Completa**

Vedi documento dettagliato: **`TEST_MANUALI_VS_AUTOMATICI.md`**

---

### **🤖 Test Automatizzati (80% del lavoro) - GIÀ FATTI**

**✅ Tutti i test automatizzati sono già pronti!**

**Come eseguire:**
```bash
# Test rapidi (senza pytest, funziona subito)
cd email-agent-service
python3 tests/quick_test_booking.py

# Test completi (con pytest, richiede dipendenze)
pytest tests/unit/test_booking_*.py -v

# Test specifici
pytest tests/unit/test_booking_models.py -v
pytest tests/unit/test_booking_messaging_client.py -v
pytest tests/unit/test_booking_reservation_client.py -v
```

**Cosa viene testato automaticamente:**
- ✅ **Modelli dati** (`test_booking_models.py`) - Creato ✅
- ✅ **Messaging Client** con mock (`test_booking_messaging_client.py`) - Creato ✅
- ✅ **Reservation Client** con mock (`test_booking_reservation_client.py`) - Creato ✅
- ✅ **Conversioni formati** - Test inclusi ✅
- ⏳ **Parser XML** - Da creare quando parser è fatto
- ⏳ **Business logic** - Da creare quando servizi sono fatti

**Quando eseguire:**
- ✅ Durante sviluppo (automatically via IDE)
- ✅ Prima di ogni commit
- ✅ In CI/CD pipeline

**Risultato:** Tutti i test passano in mock mode, senza bisogno di credenziali! ✅

---

### **👤 Test Manuali (20% del lavoro) - QUANDO SERVE**

**⚠️ IMPORTANTE: NON serve test manuale durante sviluppo normale!**

**Fai test manuali SOLO quando:**

#### **1. 🎯 SCENARIO 1: Hai appena ottenuto credenziali** (1-2 ore)
**Quando:** Dopo T0.1 (credenziali ottenute)

**Cosa testare:**
- Verifica autenticazione API reali
- Verifica formato response reali vs mock
- Aggiustamento mock se necessario

**Comandi:**
```bash
# Test autenticazione
curl -u "USERNAME:PASSWORD" \
     -H "Accept-Version: 1.2" \
     https://supply-xml.booking.com/messaging/messages/latest
```

#### **2. 🎯 SCENARIO 2: Prima integrazione end-to-end** (2-4 ore)
**Quando:** Dopo Fase 3 (integrazione completa)

**Cosa testare:**
- Test flusso completo messaggi (guest → sistema → risposta)
- Test flusso completo prenotazioni (booking → import → Firestore)
- Edge cases reali

#### **3. 🎯 SCENARIO 3: Prima di deploy produzione** (1 giorno)
**Quando:** Dopo Fase 4 (testing e refinement)

**Cosa testare:**
- Certificazione Booking.com
- Test performance
- Test produzione su staging

#### **4. 🎯 SCENARIO 4: Debug problemi specifici** (variabile)
**Quando:** Quando trovi un bug specifico

**Cosa testare:**
- Riprodurre problema con API reali
- Verifica fix con API reali

---

### **📋 Checklist Test per Ogni Fase**

| Fase | Test Automatici | Test Manuali | Quando Test Manuali |
|------|----------------|--------------|---------------------|
| **Fase 0-1** | ✅ FATTI | ❌ NON NECESSARI | Non hai credenziali |
| **Fase 2A** | ⏳ DA FARE | ⏳ DOPO credenziali | Quando ottieni credenziali |
| **Fase 2B** | ⏳ DA FARE | ⏳ DOPO credenziali | Quando ottieni credenziali |
| **Fase 3** | ⏳ DA FARE | ⏳ DOPO integrazione | Dopo integrazione + credenziali |
| **Fase 4** | ⏳ DA FARE | ⏳ Edge cases | Dopo credenziali |
| **Fase 5** | ⏳ CI/CD | ⏳ Certificazione | Prima di produzione |

---

### **💡 Raccomandazioni**

#### **✅ FAI:**
- ✅ Test automatici per tutto ciò che puoi
- ✅ Test manuali solo quando hai credenziali
- ✅ Test manuali solo per verifiche API reali
- ✅ Aggiungi test automatici dopo ogni bug trovato manualmente

#### **❌ NON FARE:**
- ❌ Test manuali durante sviluppo normale (inutile)
- ❌ Test manuali senza credenziali (non funzionano)
- ❌ Test manuali per cose che puoi testare automaticamente
- ❌ Dimenticare di aggiungere test automatici dopo test manuali

---

### **⏰ Timeline Test Manuali**

**Quand'è il momento di iniziare test manuali?**

1. **❌ NON ADESSO** - Stai ancora sviluppando, non hai credenziali
2. **✅ QUANDO OTTIENI CREDENZIALI** (Scenario 1) - Verifica autenticazione (1-2 ore)
3. **✅ DOPO INTEGRAZIONE COMPLETA** (Scenario 2) - Test flusso completo (2-4 ore)
4. **✅ PRIMA DI PRODUZIONE** (Scenario 3) - Certificazione Booking.com (1 giorno)

**Totale test manuali stimati:** 10-20 ore (vs 100+ ore di sviluppo)

---

### **📚 Riferimenti**

- **`TEST_MANUALI_VS_AUTOMATICI.md`** - Documentazione completa dettagliata
- **`tests/quick_test_booking.py`** - Script test rapido (eseguibile subito)
- **`tests/unit/test_booking_*.py`** - Test unit completi (con pytest)
- **`tests/fixtures/booking_api_responses.py`** - Mock responses per test

---

## ✅ Next Steps

**Prossimi task da iniziare SUBITO:**
1. ✅ **T1.1** Configurazione (senza credenziali reali) - COMPLETATO
2. ✅ **T1.8-T1.9** Modelli dati - COMPLETATO
3. ✅ **T1.4-T1.6** Client API con mock mode - COMPLETATO
4. ✅ **T1.10** Test automatizzati - COMPLETATO

**Prossimi task (Fase 2A - Import Prenotazioni):**
1. **T2A.1** Parser XML OTA (può essere fatto con mock XML)
2. **T2A.3** Polling Service (con mock client)
3. **T2A.5** Persistence Service

**In parallelo:**
- 🔄 **T0.1** Richiedere credenziali Machine Account Booking.com

**Una volta ottenute credenziali:**
- Sostituire mock con chiamate reali
- Test integration reali (test manuali)
- Test end-to-end completo (test manuali)

