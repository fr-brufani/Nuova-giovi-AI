# Verifica Gmail Watch in Firestore

## 📍 Dove cercare

**Collezione:** `hostEmailIntegrations`  
**Documento ID:** `{TUA_EMAIL_GMAIL}` (es: `tuaemail@gmail.com`)

---

## ✅ Cosa dovrebbe apparire dopo l'attivazione

### Struttura del documento `hostEmailIntegrations/{EMAIL}`:

```json
{
  "emailAddress": "tuaemail@gmail.com",
  "hostId": "host-id-123",
  "provider": "gmail",
  "encryptedAccessToken": "...",
  "encryptedRefreshToken": "...",
  "scopes": [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.readonly"
  ],
  "status": "active",  // ← CAMBIATO da "connected" a "active"
  "pmsProvider": "scidoo",  // o "booking", "airbnb", etc.
  
  // ← NUOVI CAMPI AGGIUNTI:
  "watchSubscription": {
    "historyId": "123456789",  // ← ID fornito da Gmail API
    "expiration": Timestamp(1734893332000)  // ← Timestamp ~7 giorni nel futuro
  },
  "lastHistoryIdProcessed": "123456789",  // ← Aggiornato con historyId
  
  "createdAt": Timestamp(...),
  "updatedAt": Timestamp(now)  // ← Aggiornato a ora
}
```

---

## 🔍 Come verificare

### Opzione 1: Firebase Console (UI)

1. Vai su [Firebase Console](https://console.firebase.google.com/)
2. Seleziona progetto: `giovi-ai`
3. Vai su **Firestore Database**
4. Apri collezione: `hostEmailIntegrations`
5. Trova documento con ID = `{TUA_EMAIL_GMAIL}`
6. Verifica presenza di:
   - ✅ Campo `watchSubscription` (oggetto con `historyId` e `expiration`)
   - ✅ Campo `status` = `"active"`
   - ✅ Campo `lastHistoryIdProcessed` (stringa con ID)

### Opzione 2: gcloud CLI

```bash
# Sostituisci [EMAIL] con la tua email Gmail
gcloud firestore documents get \
  projects/giovi-ai/databases/(default)/documents/hostEmailIntegrations/[EMAIL] \
  --project giovi-ai
```

**Output atteso:**
```json
{
  "name": "projects/giovi-ai/databases/(default)/documents/hostEmailIntegrations/tuaemail@gmail.com",
  "fields": {
    "emailAddress": {
      "stringValue": "tuaemail@gmail.com"
    },
    "hostId": {
      "stringValue": "host-id-123"
    },
    "status": {
      "stringValue": "active"
    },
    "watchSubscription": {
      "mapValue": {
        "fields": {
          "historyId": {
            "stringValue": "123456789"
          },
          "expiration": {
            "timestampValue": "2025-11-21T20:28:52Z"
          }
        }
      }
    },
    "lastHistoryIdProcessed": {
      "stringValue": "123456789"
    },
    "updatedAt": {
      "timestampValue": "2025-11-14T19:28:52Z"
    }
  }
}
```

### Opzione 3: Python Script

```python
from firebase_admin import firestore
import firebase_admin

# Inizializza Firebase (se non già fatto)
if not firebase_admin._apps:
    firebase_admin.initialize_app()

db = firestore.Client()

# Leggi documento
email = "tuaemail@gmail.com"
doc_ref = db.collection("hostEmailIntegrations").document(email)
doc = doc_ref.get()

if doc.exists:
    data = doc.to_dict()
    print(f"Status: {data.get('status')}")
    print(f"Watch Subscription: {data.get('watchSubscription')}")
    print(f"Last History ID: {data.get('lastHistoryIdProcessed')}")
else:
    print("Documento non trovato")
```

---

## 📊 Campi chiave da verificare

### 1. `watchSubscription` (NUOVO)
- **Tipo:** Oggetto/Map
- **Contenuto:**
  - `historyId`: Stringa con ID fornito da Gmail
  - `expiration`: Timestamp Firestore (~7 giorni nel futuro)
- **Esempio:**
  ```json
  {
    "historyId": "123456789",
    "expiration": Timestamp(1734893332000)  // 21/11/2025, 20:28:52
  }
  ```

### 2. `status` (AGGIORNATO)
- **Prima:** `"connected"`
- **Dopo:** `"active"`
- **Significato:** Indica che il watch è attivo

### 3. `lastHistoryIdProcessed` (AGGIORNATO)
- **Tipo:** Stringa
- **Valore:** Stesso `historyId` di `watchSubscription`
- **Significato:** ID dell'ultima email processata (usato per evitare duplicati)

### 4. `updatedAt` (AGGIORNATO)
- **Tipo:** Timestamp Firestore
- **Valore:** Timestamp corrente al momento dell'attivazione

---

## ⚠️ Se NON vedi questi campi

### Possibili problemi:

1. **`watchSubscription` mancante:**
   - Il watch non è stato salvato correttamente
   - Verifica log Cloud Run per errori

2. **`status` ancora `"connected"`:**
   - Il watch non è stato attivato
   - Riprova a cliccare "Attiva notifiche email"

3. **`expiration` nel passato:**
   - Il watch è scaduto (dopo 7 giorni)
   - Rinnova cliccando di nuovo "Attiva notifiche email"

---

## 🔄 Dopo l'attivazione

Una volta verificato che `watchSubscription` esiste in Firestore:

1. **Gmail invierà notifiche** quando arrivano nuove email rilevanti
2. **Pub/Sub riceverà le notifiche** e le inoltrerà al servizio
3. **Il servizio processerà le email** e le salverà in:
   - `properties` (se conferma prenotazione)
   - `reservations` (prenotazioni)
   - `clients` (clienti)
   - `properties/{propertyId}/conversations/{clientId}/messages` (messaggi guest)

---

## 📝 Note importanti

- **Scadenza:** Il watch scade dopo **7 giorni** (limite Gmail)
- **Rinnovo:** Serve rinnovare manualmente o configurare Cloud Scheduler
- **History ID:** Usato per tracciare le email già processate
- **Filtri:** Solo email rilevanti vengono processate (basate su `pmsProvider`)

