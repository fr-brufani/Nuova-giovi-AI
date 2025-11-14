# 📊 Stato Progetto - Email Agent Service

**Data Aggiornamento:** 14 Novembre 2025  
**Versione:** Step 1-3 Completati

---

## 🎯 Obiettivo del Progetto

Creare un servizio attivo 24/7 che permetta di:
1. **Collegare caselle Gmail** dei property manager
2. **Importare email prenotazioni** (Booking.com e Airbnb) degli ultimi 6 mesi
3. **Estrarre e salvare** prenotazioni, clienti e property in Firestore
4. **Monitorare in tempo reale** nuove email
5. **Rispondere automaticamente** ai messaggi degli ospiti usando Gemini AI
6. **Salvare le risposte AI** in Firestore

---

## ✅ COSA È STATO SVILUPPATO (Step 1-3)

### **Step 1: Setup Base** ✅ COMPLETATO

**Stato:** Funziona correttamente

**Cosa fa:**
- Servizio FastAPI configurato e funzionante
- Integrazione Firebase Admin (Firestore)
- Health check endpoint: `GET /health/live`
- CORS configurato per frontend (localhost:8080, :3000)
- Dependency injection per servizi e repository
- Configurazione con Pydantic Settings
- Cifratura token con Fernet

**File principali:**
- `src/email_agent_service/app.py` - Configurazione FastAPI app
- `src/email_agent_service/dependencies/firebase.py` - Firebase initialization
- `src/email_agent_service/config/settings.py` - Configurazione app
- `src/email_agent_service/utils/crypto.py` - Cifratura token

**Test:** ✅ 1 test passato

---

### **Step 2: OAuth Gmail** ✅ COMPLETATO E TESTATO

**Stato:** Funziona correttamente per tutti gli utenti

**Cosa fa:**
- Endpoint `POST /integrations/gmail/start` - Inizia flusso OAuth
- Endpoint `POST /integrations/gmail/callback` - Completa OAuth
- Cifratura access token e refresh token (Fernet)
- Salvataggio integrazione in Firestore (`hostEmailIntegrations`)
- Pulizia automatica OAuth states scaduti

**File principali:**
- `src/email_agent_service/api/routes/integrations.py` - Endpoint OAuth
- `src/email_agent_service/services/integrations/oauth_service.py` - Logica OAuth
- `src/email_agent_service/repositories/oauth_states.py` - Repository OAuth states
- `src/email_agent_service/repositories/host_email_integrations.py` - Repository integrazioni

**Frontend:**
- `giovi/frontend/giovi-ai-working-app/src/components/settings/GmailIntegrationCard.tsx` - UI OAuth
- `giovi/frontend/giovi-ai-working-app/src/pages/GmailCallback.tsx` - Callback page

**Test:** ✅ 5 test passati (OAuth service + routes)

**Verifica manuale:** ✅ Testato con 2 account Gmail diversi - funziona correttamente

---

### **Step 3: Backfill & Parsing** ✅ COMPLETATO E TESTATO

**Stato:** Funziona correttamente con email reali

**Cosa fa:**
- Endpoint `POST /integrations/gmail/{email}/backfill?host_id=...` - Import email ultimi 6 mesi
- Estrazione email da Gmail API con query specifica per Booking/Airbnb
- Parser Booking.com (conferme prenotazioni + messaggi ospite)
- Parser Airbnb (conferme prenotazioni + messaggi ospite)
- Deduplica messaggi processati (evita duplicati)
- Restituisce dati parsati in formato JSON

**Query Gmail utilizzata:**
```
(from:@mchat.booking.com OR from:@scidoo.com OR 
 from:@reply.airbnb.com OR from:automated@airbnb.com) 
AND after:YYYY/MM/DD
```
Dove `YYYY/MM/DD` è la data di 180 giorni fa (6 mesi).

**File principali:**
- `src/email_agent_service/api/routes/integrations.py` - Endpoint backfill
- `src/email_agent_service/services/backfill_service.py` - Logica backfill
- `src/email_agent_service/services/gmail_service.py` - Wrapper Gmail API
- `src/email_agent_service/parsers/` - Parser email (Booking/Airbnb)
- `src/email_agent_service/repositories/processed_messages.py` - Deduplica

**Test:** ✅ 4 test passati (parsers) + 1 test backfill

**Verifica manuale:** ✅ Testato con account reale - trova e parsa correttamente email Booking/Airbnb

**⚠️ NOTA IMPORTANTE - Query Gmail:**
La query attuale potrebbe essere troppo restrittiva. Filtra solo questi mittenti:
- Booking: `@mchat.booking.com`, `@scidoo.com`
- Airbnb: `@reply.airbnb.com`, `@automated@airbnb.com`

Potrebbero esistere altre varianti di mittenti Booking/Airbnb che non vengono incluse. Se si trovano solo poche email, potrebbe essere necessario espandere la query.

**⚠️ PROBLEMA RISOLTO:**
Era presente un bug con `token_expiry` (datetime timezone-aware vs naive) che causava errori 500 durante il backfill. **RISOLTO** rimuovendo l'impostazione manuale di `expiry` e lasciando che Google OAuth lo gestisca automaticamente.

---

## ❌ COSA NON È ANCORA IMPLEMENTATO (Step 4-8)

### **Step 4: Persistenza Automatica** ❌ NON IMPLEMENTATO

**Stato:** Priorità ALTA - Da implementare prossimamente

**Cosa manca:**
- ❌ Salvataggio automatico prenotazioni in Firestore (`reservations`)
- ❌ Salvataggio automatico clienti in Firestore (`clients`)
- ❌ Salvataggio automatico property in Firestore (`properties`)
- ❌ Linking tra prenotazioni, clienti e property
- ❌ Aggiornamento prenotazioni esistenti (se già presenti)

**Stato attuale:**
Il parsing funziona correttamente e restituisce dati strutturati, ma **i dati non vengono salvati in Firestore**. Vengono solo restituiti nella risposta JSON dell'endpoint backfill.

**Cosa serve:**
1. Creare service/repository per salvare prenotazioni
2. Creare service/repository per salvare clienti
3. Creare service/repository per salvare property
4. Modificare `backfill_service.py` per salvare i dati dopo il parsing
5. Gestire linking tra entità (prenotazione → cliente, prenotazione → property)

**Schema Firestore da usare:**
Vedi `giovi/MDs/firestore_structure.json` (se esiste) oppure `FLUSSO_COMPLETO.md` per lo schema previsto.

**Priorità:** ALTA - Questo è il prossimo step da implementare.

---

### **Step 5: Gmail Watch** ❌ NON IMPLEMENTATO

**Stato:** Priorità MEDIA - Dopo Step 4

**Cosa manca:**
- ❌ Setup Gmail watch per notifiche real-time
- ❌ Endpoint per gestire notifiche Pub/Sub da Gmail
- ❌ Refresh automatico watch (ogni 7 giorni tramite Cloud Scheduler)
- ❌ Configurazione Pub/Sub topic in GCP

**Cosa serve:**
1. Endpoint `POST /integrations/gmail/{email}/watch` - Setup watch
2. Endpoint `POST /integrations/gmail/notifications` - Handler Pub/Sub
3. Cloud Scheduler job per refresh watch ogni 7 giorni
4. Configurazione Pub/Sub topic `gmail-notifications-giovi-ai` in GCP

---

### **Step 6: Pipeline Messaggi Guest** ❌ NON IMPLEMENTATO

**Stato:** Priorità MEDIA - Dopo Step 5

**Cosa manca:**
- ❌ Rilevamento messaggi guest in tempo reale (da Gmail watch)
- ❌ Verifica `autoReplyEnabled` per cliente (flag in Firestore `clients`)
- ❌ Estrazione contesto conversazione (storia messaggi)
- ❌ Identificazione prenotazione collegata al messaggio

**Cosa serve:**
1. Service per processare notifiche Gmail
2. Logica per identificare messaggi guest (Booking/Airbnb)
3. Query Firestore per verificare `autoReplyEnabled` del cliente
4. Estrazione contesto conversazione da Firestore o Gmail

---

### **Step 7: Integrazione Gemini AI** ❌ NON IMPLEMENTATO

**Stato:** Priorità MEDIA - Dopo Step 6

**Cosa manca:**
- ❌ Chiamata a Gemini API per generare risposte
- ❌ Costruzione prompt con contesto (property, prenotazione, conversazione)
- ❌ Gestione conversazioni (storia messaggi)
- ❌ Configurazione API key Gemini

**Prompt esempio (da implementare):**
```
Sei "Giovi AI", un assistente concierge virtuale amichevole, preciso e disponibile per l'alloggio chiamato "${propertyData.name}".

Il tuo compito è:
- Se la domanda è informativa e l'informazione è presente nel contesto fornito, rispondi in modo completo.
- Se l'informazione richiesta NON è presente o è incompleta: Rispondi: "Mi dispiacere, non ho questa informazione specifica nei dettagli forniti dall'host." NON inventare dettagli.
- Se la domanda è ambigua, chiedi gentilmente di specificare meglio.
- Se hai già risposto a domande simili nelle conversazioni precedenti, puoi fare riferimento a quelle risposte per mantenere coerenza.

Rispondi in modo cortese e con frasi complete.
```

**Cosa serve:**
1. Configurazione Gemini API key (Secret Manager)
2. Service per chiamare Gemini API
3. Costruzione prompt dinamico con contesto
4. Parsing risposta da Gemini

---

### **Step 8: Invio Email Reply** ❌ NON IMPLEMENTATO

**Stato:** Priorità MEDIA - Dopo Step 7

**Cosa manca:**
- ❌ Invio email reply tramite Gmail API (usando `reply-to` dalla mail originale)
- ❌ Salvataggio risposte AI in Firestore (`aiResponses` collection)
- ❌ Tracking messaggi inviati (evitare duplicati)

**Cosa serve:**
1. Modifica `gmail_service.py` per aggiungere metodo `send_reply()`
2. Logica per costruire email reply (threading per Airbnb)
3. Repository per salvare risposte AI
4. Tracking messaggi inviati (evitare risposte duplicate)

---

## 📊 STATISTICHE PROGETTO

- **File Python:** 27
- **Test unitari:** 17/17 passati (100%)
- **Endpoint API:** 3 principali + health
- **Parser implementati:** 4 (Booking/Airbnb conferme + messaggi)
- **Repository:** 3 (OAuthStates, HostEmailIntegrations, ProcessedMessages)
- **Servizi:** 3 (OAuth, Gmail, Backfill)

---

## 🔍 ANALISI PROBLEMA: PERCHÉ SOLO 2 EMAIL TROVATE?

**Contesto:**
Durante il test del backfill con account `shortdeseos@gmail.com`, il sistema ha trovato solo 2 email negli ultimi 6 mesi.

**Possibili cause:**

1. **✅ SONO EFFETTIVAMENTE SOLO 2 EMAIL**
   - L'account potrebbe avere davvero solo 2 email Booking/Airbnb
   - Potrebbe essere un account di test con poche prenotazioni
   - Potrebbe essere un account nuovo con poche attività

2. **⚠️ QUERY GMAIL TROPPO RESTRITTIVA**
   - La query attuale filtra solo questi mittenti:
     - Booking: `@mchat.booking.com`, `@scidoo.com`
     - Airbnb: `@reply.airbnb.com`, `@automated@airbnb.com`
   - Potrebbero esistere altre varianti di mittenti Booking/Airbnb che non vengono incluse
   - Esempi possibili: `@booking.com`, `@airbnb.com`, `@email.booking.com`, ecc.

3. **⚠️ EMAIL PIÙ VECCHIE DI 6 MESI**
   - Il sistema cerca solo email degli ultimi 180 giorni
   - Se le prenotazioni sono più vecchie, non vengono incluse

4. **⚠️ EMAIL GIÀ PROCESSATE (se eseguito più volte)**
   - Il sistema marca email come "processate" in `processedMessageIds`
   - Se esegui l'import più volte, vede solo nuove email
   - Ma questa dovrebbe essere la prima volta

**Cosa verificare:**
- Quante email ci sono realmente in quella casella Gmail?
- Quali sono i mittenti reali delle email Booking/Airbnb?
- Le email sono più vecchie di 6 mesi?

**Soluzione potenziale:**
Se necessario, espandere la query Gmail per includere più varianti di mittenti Booking/Airbnb. Questo può essere fatto modificando `_build_query()` in `backfill_service.py`.

---

## 🚀 PROSSIMI PASSI - GUIDA IMPLEMENTAZIONE

### **PASSO 1: Implementare Step 4 - Persistenza Automatica** (Priorità ALTA)

**Obiettivo:** Salvare prenotazioni, clienti e property in Firestore dopo il parsing.

**Cosa fare:**

1. **Creare repository per prenotazioni, clienti e property**
   - File: `src/email_agent_service/repositories/reservations.py`
   - File: `src/email_agent_service/repositories/clients.py`
   - File: `src/email_agent_service/repositories/properties.py`
   - Metodi: `upsert()`, `get()`, `get_by_reservation_id()`, ecc.

2. **Creare service per salvare dati parsati**
   - File: `src/email_agent_service/services/persistence_service.py`
   - Metodo: `save_parsed_email(parsed_email: ParsedEmail, host_id: str)`
   - Logica:
     - Se `kind == booking_confirmation` o `airbnb_confirmation`:
       - Salva/aggiorna prenotazione in `reservations`
       - Salva/aggiorna cliente in `clients`
       - Salva/aggiorna property in `properties`
       - Collega prenotazione → cliente, prenotazione → property
     - Se `kind == booking_message` o `airbnb_message`:
       - Trova prenotazione collegata (per reservation ID)
       - Salva messaggio nella conversazione (se necessario)

3. **Modificare `backfill_service.py`**
   - Dopo il parsing, chiamare `persistence_service.save_parsed_email()`
   - Gestire errori (salvare comunque se possibile)

4. **Schema Firestore:**
   - Consultare `giovi/MDs/firestore_structure.json` per schema previsto
   - Oppure documentazione esistente in `FLUSSO_COMPLETO.md`

5. **Test:**
   - Test unitari per repository
   - Test integrazione backfill + persistenza
   - Verifica manuale: eseguire backfill e verificare dati in Firestore

---

### **PASSO 2: Implementare Step 5 - Gmail Watch** (Priorità MEDIA)

**Obiettivo:** Setup Gmail watch per notifiche real-time di nuove email.

**Cosa fare:**

1. **Creare endpoint per setup watch**
   - Endpoint: `POST /integrations/gmail/{email}/watch`
   - Chiama Gmail API `users().watch()` per l'email
   - Salva subscription info in Firestore (`watchSubscription` in `hostEmailIntegrations`)

2. **Creare endpoint per gestire notifiche Pub/Sub**
   - Endpoint: `POST /integrations/gmail/notifications`
   - Riceve notifiche da Gmail via Pub/Sub
   - Processa nuove email (parsing + persistenza)

3. **Configurare Pub/Sub in GCP**
   - Creare topic `gmail-notifications-giovi-ai`
   - Configurare subscription
   - Impostare webhook per endpoint notifiche

4. **Cloud Scheduler per refresh watch**
   - Watch scade dopo 7 giorni
   - Creare Cloud Scheduler job per refresh automatico
   - Chiama endpoint setup watch ogni 7 giorni

---

### **PASSO 3-4: Implementare Step 6-8 - Pipeline AI Reply** (Priorità MEDIA)

**Vedi documentazione completa in `FLUSSO_COMPLETO.md` per dettagli.**

---

## 📝 NOTE TECNICHE IMPORTANTI

### **Configurazione Ambiente**

**Variabili d'ambiente necessarie (`.env`):**
```bash
TOKEN_ENCRYPTION_KEY=<chiave Fernet 32 bytes base64>
GOOGLE_OAUTH_CLIENT_ID=<client-id>.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=<client-secret>
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8080/integrations/gmail/callback
FIREBASE_CREDENTIALS_PATH=/path/to/firebase-credentials.json
FIREBASE_PROJECT_ID=giovi-ai
```

### **Problemi Risolti**

1. **Errore "Scope has changed" durante OAuth callback**
   - **Causa:** Google aggiunge automaticamente scope extra (`openid`, `userinfo.email`, `userinfo.profile`)
   - **Soluzione:** Impostato `OAUTHLIB_RELAX_TOKEN_SCOPE='1'` prima di `fetch_token()`

2. **Errore "TypeError: can't compare offset-naive and offset-aware datetimes"**
   - **Causa:** `token_expiry` non era timezone-aware quando confrontato con datetime di Google
   - **Soluzione:** Rimossa impostazione manuale di `expiry` - Google OAuth lo gestisce automaticamente

### **Struttura Codice**

```
email-agent-service/
├── src/email_agent_service/
│   ├── api/routes/          # Endpoint API
│   ├── config/              # Configurazione
│   ├── dependencies/        # Dependency injection
│   ├── models/              # Pydantic models
│   ├── parsers/             # Parser email
│   ├── repositories/        # Firestore repositories
│   ├── services/            # Business logic
│   └── utils/               # Utility
└── tests/                   # Test unitari
```

---

## ✅ CHECKLIST PER NUOVO AGENTE

Se stai continuando il lavoro, verifica:

- [ ] Backend è avviato e risponde (`GET /health/live`)
- [ ] Frontend è avviato e si connette al backend
- [ ] OAuth Gmail funziona (test con account reale)
- [ ] Backfill funziona (test con account reale)
- [ ] Parsing funziona (email Booking/Airbnb vengono parsate correttamente)
- [ ] I dati vengono salvati in Firestore? (❌ NO - Step 4 da implementare)

**Prossimo step da implementare:** Step 4 - Persistenza Automatica

---

## 📚 DOCUMENTAZIONE AGGIUNTIVA

- `FLUSSO_COMPLETO.md` - Dettagli tecnici dei flussi
- `README.md` - Guida setup e test
- `giovi/MDs/AI_Email_Agent_Service_Tech_Design.md` - Design tecnico originale

---

**Ultimo aggiornamento:** 14 Novembre 2025  
**Stato attuale:** Step 1-3 completati ✅ | Step 4-8 da implementare ❌

