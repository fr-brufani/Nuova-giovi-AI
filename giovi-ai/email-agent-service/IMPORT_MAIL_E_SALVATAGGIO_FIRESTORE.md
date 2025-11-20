# 📧 Import Mail e Salvataggio in Firestore - Email Agent Service

## 📋 Panoramica

Il servizio `email-agent-service` si occupa di:
1. **Importare email** dalla casella Gmail dell'host (in particolare email di Airbnb e Booking)
2. **Parsare le email** per estrarre informazioni su prenotazioni, clienti e property
3. **Salvare i dati** in Firestore nelle collezioni `reservations`, `clients` e `properties`

---

## 🔄 Flusso Completo

### **1. Autenticazione OAuth Gmail**

**Endpoint:** `POST /integrations/gmail/start` → `POST /integrations/gmail/callback`

**File coinvolti:**
- `services/integrations/oauth_service.py` - Gestisce il flusso OAuth
- `repositories/host_email_integrations.py` - Salva token cifrati in Firestore

**Cosa succede:**
1. L'host autorizza l'accesso alla sua casella Gmail tramite OAuth
2. I token di accesso/refresh vengono cifrati con Fernet e salvati in Firestore
3. Documento salvato: `hostEmailIntegrations/{email}` con token cifrati

---

### **2. Import Email (Backfill)**

**Endpoint:** `POST /integrations/gmail/{email}/backfill?host_id={host_id}`

**File principale:** `services/backfill_service.py`

#### **Fase 1: Recupero Email da Gmail**

**File:** `services/gmail_service.py`

```python
# Query Gmail per email degli ultimi 6 mesi
query = "(from:automated@airbnb.com OR from:reservation@scidoo.com) AND after:{date}"
messages = gmail_service.list_messages(integration, query=query)
```

**Filtri applicati:**
- **Airbnb:** `from:automated@airbnb.com` (conferme e cancellazioni)
- **Booking (via Scidoo):** `from:reservation@scidoo.com` con subject "Booking"
- **Modalità Airbnb Only:** Se `hosts/{host_id}.airbnbOnly = true`, cerca solo email Airbnb

**Deduplica:**
- Controlla `hostEmailIntegrations/{email}/processedMessageIds/{messageId}`
- Se già processata, viene saltata (a meno di `force=true`)

#### **Fase 2: Parsing Email**

**File:** `parsers/engine.py` - `EmailParsingEngine`

**Parser disponibili:**
1. **`AirbnbConfirmationParser`** (`parsers/airbnb_confirm.py`)
   - Estrae: `reservationId`, `threadId`, `propertyName`, `guestName`, `checkIn`, `checkOut`, `adults`, `totalAmount`
   - Tipo: `airbnb_confirmation`

2. **`AirbnbCancellationParser`** (`parsers/airbnb_cancellation.py`)
   - Estrae: `reservationId`, `threadId` per cancellare prenotazione
   - Tipo: `airbnb_cancellation`

3. **`ScidooConfirmationParser`** (`parsers/scidoo_confirm.py`)
   - Estrae: `voucherId`, `reservationId`, `propertyName`, `guestName`, `checkIn`, `checkOut`, `adults`, `totalAmount`
   - Tipo: `scidoo_confirmation`

4. **`ScidooCancellationParser`** (`parsers/scidoo_cancellation.py`)
   - Estrae: `voucherId` per cancellare prenotazione
   - Tipo: `scidoo_cancellation`

**Output parsing:**
```python
ParsedEmail(
    kind="airbnb_confirmation" | "scidoo_confirmation" | "airbnb_cancellation" | "scidoo_cancellation",
    reservation=ReservationInfo(...),  # Per conferme/cancellazioni
    metadata=ParsedEmailMetadata(...)
)
```

#### **Fase 3: Salvataggio in Firestore**

**File:** `services/persistence_service.py`

**Ordine di processamento:**
1. **PRIMA** tutte le conferme (`airbnb_confirmation`, `scidoo_confirmation`)
2. **POI** tutte le cancellazioni (`airbnb_cancellation`, `scidoo_cancellation`)
3. **INFINE** altre email (messaggi, ecc.)

**Per ogni conferma:**

**A. Trova/Crea Property**
- **Repository:** `repositories/properties.py`
- **Query:** Cerca `properties` dove `name == propertyName` AND `hostId == host_id`
- **Se non esiste:** Crea nuovo documento in `properties/{autoId}`
- **Campi salvati:**
  ```json
  {
    "name": "MAGGIORE SUITE - DUOMO DI PERUGIA",
    "hostId": "host-xyz",
    "createdAt": "2025-01-15T10:00:00Z",
    "lastUpdatedAt": "2025-01-15T10:00:00Z",
    "importedFrom": "airbnb_email" | "scidoo_email"
  }
  ```

**B. Trova/Crea Cliente**
- **Repository:** `repositories/clients.py`
- **Query:** Cerca `clients` dove `email == guestEmail` (case-insensitive)
- **Se non esiste:** Cerca per `name == guestName` AND `assignedHostId == host_id`
- **Se ancora non esiste:** Crea nuovo documento in `clients/{autoId}`
- **Campi salvati:**
  ```json
  {
    "role": "guest",
    "name": "Francesco Brufani",
    "email": "francesco@example.com",
    "whatsappPhoneNumber": "+393315681407",
    "assignedHostId": "host-xyz",
    "assignedPropertyId": "property-abc",
    "reservationId": "ABC123",
    "createdAt": "2025-01-15T10:00:00Z",
    "lastUpdatedAt": "2025-01-15T10:00:00Z",
    "importedFrom": "airbnb_email" | "scidoo_email"
  }
  ```

**C. Crea/Aggiorna Prenotazione**
- **Repository:** `repositories/reservations.py`
- **Query:** Cerca `reservations` dove `reservationId == reservationId` OR `voucherId == voucherId` AND `hostId == host_id`
- **Se esiste:** Aggiorna documento esistente (merge)
- **Se non esiste:** Crea nuovo documento in `reservations/{autoId}`
- **Campi salvati:**
  ```json
  {
    "reservationId": "ABC123",  // Per Airbnb
    "voucherId": "VOUCHER456",  // Per Booking/Scidoo
    "threadId": "123456",  // Per Airbnb (per matchare messaggi)
    "hostId": "host-xyz",
    "propertyId": "property-abc",
    "propertyName": "MAGGIORE SUITE - DUOMO DI PERUGIA",
    "clientId": "client-xyz",
    "clientName": "Francesco Brufani",
    "startDate": "2026-01-15T00:00:00Z",
    "endDate": "2026-01-18T00:00:00Z",
    "status": "confirmed",
    "totalPrice": 318.00,
    "adults": 2,
    "sourceChannel": "airbnb" | "booking",
    "createdAt": "2025-01-15T10:00:00Z",
    "lastUpdatedAt": "2025-01-15T10:00:00Z",
    "importedFrom": "airbnb_email" | "scidoo_email"
  }
  ```

**Per ogni cancellazione:**

**A. Cerca Prenotazione da Cancellare**
- **Scidoo:** Cerca per `voucherId`
- **Airbnb:** Cerca per `reservationId` o `threadId`

**B. Aggiorna Status**
- Imposta `status = "cancelled"`
- Aggiunge `cancellationDetails` con timestamp

#### **Fase 4: Marca Email come Processata**

**File:** `repositories/processed_messages.py`

**Salvataggio:**
```
hostEmailIntegrations/{email}/processedMessageIds/{messageId}
```

**Campi:**
```json
{
  "historyId": "12345",
  "processedAt": "2025-01-15T10:00:00Z"
}
```

Questo evita di processare la stessa email due volte.

---

## 📊 Struttura Firestore

### **Collezioni Principali**

#### **1. `hostEmailIntegrations/{email}`**
Integrazione Gmail dell'host
```json
{
  "hostId": "host-xyz",
  "email": "shortdeseos@gmail.com",
  "encryptedAccessToken": "...",
  "encryptedRefreshToken": "...",
  "scopes": ["https://www.googleapis.com/auth/gmail.readonly", ...],
  "status": "connected",
  "watchHistoryId": "12345",
  "watchExpiration": 1737129600000
}
```

**Subcollection:** `processedMessageIds/{messageId}`
- Traccia email già processate

#### **2. `properties/{propertyId}`**
Property dell'host
```json
{
  "name": "MAGGIORE SUITE - DUOMO DI PERUGIA",
  "hostId": "host-xyz",
  "createdAt": "2025-01-15T10:00:00Z",
  "lastUpdatedAt": "2025-01-15T10:00:00Z",
  "importedFrom": "airbnb_email"
}
```

#### **3. `clients/{clientId}`**
Clienti (ospiti)
```json
{
  "role": "guest",
  "name": "Francesco Brufani",
  "email": "francesco@example.com",
  "whatsappPhoneNumber": "+393315681407",
  "assignedHostId": "host-xyz",
  "assignedPropertyId": "property-abc",
  "reservationId": "ABC123",
  "createdAt": "2025-01-15T10:00:00Z",
  "lastUpdatedAt": "2025-01-15T10:00:00Z",
  "importedFrom": "airbnb_email"
}
```

#### **4. `reservations/{reservationId}`**
Prenotazioni
```json
{
  "reservationId": "ABC123",
  "voucherId": "VOUCHER456",
  "threadId": "123456",
  "hostId": "host-xyz",
  "propertyId": "property-abc",
  "propertyName": "MAGGIORE SUITE - DUOMO DI PERUGIA",
  "clientId": "client-xyz",
  "clientName": "Francesco Brufani",
  "startDate": "2026-01-15T00:00:00Z",
  "endDate": "2026-01-18T00:00:00Z",
  "status": "confirmed" | "cancelled",
  "totalPrice": 318.00,
  "adults": 2,
  "sourceChannel": "airbnb" | "booking",
  "createdAt": "2025-01-15T10:00:00Z",
  "lastUpdatedAt": "2025-01-15T10:00:00Z",
  "importedFrom": "airbnb_email",
  "cancellationDetails": "..." // Solo se cancellata
}
```

#### **5. `hosts/{hostId}`**
Configurazione host
```json
{
  "airbnbOnly": false  // Se true, processa solo email Airbnb
}
```

---

## 🔍 Dettagli Parsing Airbnb

### **Parser Airbnb Conferma** (`parsers/airbnb_confirm.py`)

**Estrazione dati:**

1. **Reservation ID:**
   - Pattern: `CODICE DI CONFERMA {CODE}` nel subject
   - Link: `/hosting/reservations/details/{ID}`

2. **Thread ID:**
   - Link: `/hosting/thread/{ID}`

3. **Property Name:**
   - Pattern: `MAGGIORE SUITE - DUOMO DI PERUGIA` (tutto maiuscolo con trattino)
   - Esclude: testi con "arriverà", "confermata", "nuova prenotazione"
   - Cerca in HTML: tag `h1`, `h2`, `strong`, o testo con `SUITE/CASA/APPARTAMENTO`

4. **Guest Name:**
   - Pattern: `Prenotazione confermata - {NOME} arriverà`
   - Pattern: `{NOME} arriverà`

5. **Date Check-in/Check-out:**
   - Pattern: `Check-in gio 3 set 2026` (con anno)
   - Pattern: `Check-in dom 12 ott` (senza anno, assume anno corrente/prossimo)
   - Gestisce anche formato tabella con date affiancate

6. **Adults:**
   - Pattern: `{N} adulti`

7. **Total Amount:**
   - Pattern: `TOTALE (EUR) 318,00 €`
   - Pattern: `TOTALE 318,00 €`

---

## 🚀 Come Usare

### **1. Setup OAuth Gmail**

```bash
# 1. Inizia OAuth
curl -X POST http://localhost:8000/integrations/gmail/start \
  -H "Content-Type: application/json" \
  -d '{
    "hostId": "host-xyz",
    "email": "shortdeseos@gmail.com"
  }'

# 2. Autorizza su Google (apri authorizationUrl nel browser)

# 3. Completa callback
curl -X POST http://localhost:8000/integrations/gmail/callback \
  -H "Content-Type: application/json" \
  -d '{
    "state": "...",
    "code": "...",
    "hostId": "host-xyz",
    "email": "shortdeseos@gmail.com"
  }'
```

### **2. Esegui Backfill**

```bash
# Import email degli ultimi 6 mesi
curl -X POST "http://localhost:8000/integrations/gmail/shortdeseos@gmail.com/backfill?host_id=host-xyz"

# Forza riprocessamento (anche email già processate)
curl -X POST "http://localhost:8000/integrations/gmail/shortdeseos@gmail.com/backfill?host_id=host-xyz&force=true"
```

### **3. Attiva Modalità Airbnb Only**

```bash
# Processa solo email Airbnb (ignora Booking)
curl -X PATCH "http://localhost:8000/integrations/hosts/host-xyz/airbnb-only?enabled=true"

# Torna al comportamento normale (Booking + Airbnb)
curl -X PATCH "http://localhost:8000/integrations/hosts/host-xyz/airbnb-only?enabled=false"
```

---

## 📝 Note Importanti

1. **Deduplica:** Le email vengono processate una sola volta (tranne con `force=true`)
2. **Ordine:** Le conferme vengono processate PRIMA delle cancellazioni
3. **Merge:** Se una prenotazione esiste già (per `reservationId` o `voucherId`), viene aggiornata (merge)
4. **Property/Client:** Se esistono già (per nome/email), vengono riutilizzate
5. **Airbnb Only:** Se `hosts/{host_id}.airbnbOnly = true`, vengono processate solo email Airbnb

---

## 🐛 Troubleshooting

### **Email non vengono processate**
- Verifica che l'integrazione Gmail sia attiva (`hostEmailIntegrations/{email}.status == "connected"`)
- Controlla i log del servizio per errori di parsing
- Verifica che le email corrispondano ai filtri (mittente, subject)

### **Dati non salvati in Firestore**
- Controlla i log di `persistence_service.py` per errori
- Verifica che `hostId` sia corretto
- Controlla che i dati estratti dal parser siano validi (propertyName, guestEmail, ecc.)

### **Duplicati in Firestore**
- Le prenotazioni vengono deduplicate per `reservationId` o `voucherId`
- Se ci sono duplicati, verifica che questi campi siano estratti correttamente dal parser

---

## 📚 File Chiave

- **Backfill:** `services/backfill_service.py`
- **Gmail API:** `services/gmail_service.py`
- **Persistenza:** `services/persistence_service.py`
- **Parser Airbnb:** `parsers/airbnb_confirm.py`, `parsers/airbnb_cancellation.py`
- **Repository:** `repositories/reservations.py`, `repositories/clients.py`, `repositories/properties.py`
- **API:** `api/routes/integrations.py`

