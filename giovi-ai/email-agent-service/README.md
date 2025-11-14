# Email Agent Service - Stato Implementazione

## ✅ Cosa è stato sviluppato finora

### **Step 1: Setup Base** ✅
- Progetto FastAPI completo con struttura modulare
- Integrazione Firebase Admin (Firestore)
- Health check endpoint (`GET /health`, `GET /`)
- Dependency injection per servizi e repository
- Test unitari base

### **Step 2: OAuth Gmail** ✅
- **Endpoint OAuth initiation**: `POST /integrations/gmail/start`
  - Genera URL OAuth Google con state token
  - Salva stato temporaneo in Firestore (`oauthStates`) con scadenza 10 minuti
  - Restituisce `authorizationUrl` per redirect utente
  
- **Endpoint OAuth callback**: `POST /integrations/gmail/callback`
  - Scambia authorization code per access/refresh token
  - Cifra token con Fernet (chiave da `TOKEN_ENCRYPTION_KEY`)
  - Salva integrazione in Firestore (`hostEmailIntegrations`)
  - Gestione errori (state non trovato, scaduto, token exchange fallito)

### **Step 3: Backfill & Parsing** ✅
- **Endpoint backfill**: `POST /integrations/gmail/{email}/backfill?host_id=...`
  - Scarica email degli ultimi 6 mesi da Gmail API
  - Filtra per mittenti Booking/Airbnb (query: `from:(@mchat.booking.com OR @reply.airbnb.com OR reservation@scidoo.com OR automated@airbnb.com)`)
  - Esegue deduplica via `processedMessageIds` subcollection
  - Passa ogni email ai parser

- **Parser implementati**:
  - `BookingConfirmationParser`: estrae ID prenotazione, property, date check-in/out, ospiti, totale
  - `BookingMessageParser`: estrae ID prenotazione, messaggio guest, reply-to
  - `AirbnbConfirmationParser`: estrae thread ID, property, date, ospiti, totale
  - `AirbnbMessageParser`: estrae thread ID, messaggio guest, reply-to
  
- **Output parsing**: Restituisce `ParsedEmail` con:
  - `kind`: `booking_confirmation` | `booking_message` | `airbnb_confirmation` | `airbnb_message`
  - `reservation`: `ReservationInfo` (per conferme)
  - `guestMessage`: `GuestMessageInfo` (per messaggi)
  - Metadata email (subject, sender, receivedAt)

## 🧪 Come testare

### **1. Setup Ambiente Locale**

```bash
cd giovi-ai/email-agent-service

# Attiva virtual environment
. .venv/bin/activate

# Installa dipendenze (già fatto, ma per sicurezza)
pip install -e '.[dev]'

# Configura variabili ambiente (crea un .env o esporta)
export TOKEN_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
export GOOGLE_OAUTH_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret"
export GOOGLE_OAUTH_REDIRECT_URI="http://localhost:3000/integrations/gmail/callback"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/firebase-credentials.json"  # oppure usa ADC
# Opzionale per Secret Manager:
export GCP_PROJECT_ID="your-project-id"
```

### **2. Avvia il servizio**

```bash
python main.py
# Oppure:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Il servizio sarà disponibile su `http://localhost:8000`

### **3. Test API con cURL/Postman**

#### **A. Health Check**
```bash
curl http://localhost:8000/health
# Risposta: {"status":"ok"}
```

#### **B. Inizia OAuth Flow**
```bash
curl -X POST http://localhost:8000/integrations/gmail/start \
  -H "Content-Type: application/json" \
  -d '{
    "hostId": "host-xyz",
    "email": "shortdeseos@gmail.com"
  }'
```

**Risposta esempio:**
```json
{
  "authorizationUrl": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=...&response_type=code&scope=...&state=gmail_oauth_state_abc123",
  "state": "gmail_oauth_state_abc123",
  "expiresAt": "2025-01-15T12:30:00Z"
}
```

**Apri `authorizationUrl` nel browser** → autorizza Gmail → Google redirecta a `redirect_uri` con `code` e `state`

#### **C. Completa OAuth Callback**
```bash
curl -X POST http://localhost:8000/integrations/gmail/callback \
  -H "Content-Type: application/json" \
  -d '{
    "state": "gmail_oauth_state_abc123",
    "code": "4/0AeanS...",
    "hostId": "host-xyz",
    "email": "shortdeseos@gmail.com"
  }'
```

**Risposta esempio:**
```json
{
  "status": "connected",
  "hostId": "host-xyz",
  "email": "shortdeseos@gmail.com"
}
```

#### **D. Esegui Backfill**
```bash
curl -X POST "http://localhost:8000/integrations/gmail/shortdeseos@gmail.com/backfill?host_id=host-xyz"
```

**Risposta esempio:**
```json
{
  "processed": 15,
  "items": [
    {
      "kind": "booking_confirmation",
      "reservation": {
        "reservationId": "5958915259",
        "source": "booking",
        "propertyName": "Piazza Danti Perugia Centro",
        "checkIn": "2026-01-15T00:00:00Z",
        "checkOut": "2026-01-18T00:00:00Z",
        "guestName": "Brufani Francesco",
        "guestEmail": "fbrufa.422334@guest.booking.com",
        "guestPhone": "+393315681407",
        "adults": 2,
        "totalAmount": 349.55,
        "currency": "EUR"
      },
      "guestMessage": null,
      "metadata": {...}
    },
    ...
  ]
}
```

### **4. Test da Frontend**

**✅ SÌ, puoi testare da frontend!** Ecco come:

#### **Opzione A: Integrare nel frontend esistente**

Il frontend React (`giovi-ai/giovi/frontend/giovi-ai-working-app`) può chiamare questi endpoint direttamente.

**Esempio componente React:**

```tsx
// In una pagina Settings/Integrations
const connectGmail = async () => {
  // 1. Chiama start endpoint
  const startRes = await fetch(`${API_BASE}/integrations/gmail/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      hostId: currentHostId,
      email: gmailEmail
    })
  });
  const { authorizationUrl } = await startRes.json();
  
  // 2. Redirecta utente a Google OAuth
  window.location.href = authorizationUrl;
};

// In una route callback (es. /integrations/gmail/callback)
const handleOAuthCallback = async (code: string, state: string) => {
  // 3. Completa callback
  const callbackRes = await fetch(`${API_BASE}/integrations/gmail/callback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      state,
      code,
      hostId: currentHostId,
      email: gmailEmail
    })
  });
  
  if (callbackRes.ok) {
    // 4. Opzionalmente triggera backfill
    const backfillRes = await fetch(
      `${API_BASE}/integrations/gmail/${gmailEmail}/backfill?host_id=${currentHostId}`,
      { method: 'POST' }
    );
    const { processed, items } = await backfillRes.json();
    console.log(`Processed ${processed} emails`);
  }
};
```

#### **Opzione B: Postman/Thunder Client**

Usa gli stessi endpoint sopra in Postman o Thunder Client (VS Code extension).

### **5. Verifica in Firestore**

Dopo OAuth + backfill, verifica in Firestore:

- **`hostEmailIntegrations/{email}`**: Record con token cifrati, scopes, status
- **`hostEmailIntegrations/{email}/processedMessageIds/{messageId}`**: Lista messaggi processati (deduplica)
- **`oauthStates/{state}`**: Record temporaneo (dovrebbe essere scaduto/eliminato)

## ⚠️ Cosa manca ancora

### **Step 4-8 (non ancora implementati):**
- ❌ Gmail watch (monitoraggio real-time nuovi messaggi)
- ❌ Persistenza automatica prenotazioni/clienti/property in Firestore
- ❌ Pipeline messaggi guest → risposta AI
- ❌ Integrazione Gemini per generare risposte
- ❌ Invio email reply automatico
- ❌ Endpoint stato integrazione (`GET /integrations/gmail/{email}`)

## 📝 Note Importanti

1. **Credenziali OAuth**: Devi creare un OAuth 2.0 Client in [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   - Authorized redirect URIs: aggiungi `http://localhost:3000/integrations/gmail/callback` (o il tuo frontend URL)
   - Scopes necessari: `https://www.googleapis.com/auth/gmail.readonly`, `gmail.modify`, `gmail.send`

2. **Token Encryption**: `TOKEN_ENCRYPTION_KEY` deve essere una chiave Fernet valida (32 bytes base64)

3. **Firebase Credentials**: Il servizio può usare:
   - `GOOGLE_APPLICATION_CREDENTIALS` (path a JSON)
   - Oppure Application Default Credentials (ADC) se esegui `gcloud auth application-default login`

4. **Backfill Duration**: Il backfill può richiedere diversi minuti se ci sono centinaia di email (Gmail API rate limits)

## 🧪 Test Automatici

```bash
# Esegui tutti i test unitari
pytest tests/unit

# Esegui linting
ruff check src

# Esegui type checking
mypy src
```

## 📚 Documentazione API

Il servizio espone automaticamente OpenAPI docs su:
- `http://localhost:8000/docs` (Swagger UI)
- `http://localhost:8000/redoc` (ReDoc)

