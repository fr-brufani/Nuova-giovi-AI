# 📊 Riepilogo Stato Progetto Email Agent Service

**Data:** 14 Novembre 2025  
**Stato Attuale:** Step 1-4 ✅ Completati | Step 5-8 ⏳ Da Implementare

---

## ✅ COSA È STATO COMPLETATO

### **Step 1: Setup Base** ✅
- Servizio FastAPI configurato
- Integrazione Firebase/Firestore
- Health check endpoint
- CORS configurato
- Cifratura token con Fernet

### **Step 2: OAuth Gmail** ✅
- Endpoint `/integrations/gmail/start` - Inizia OAuth
- Endpoint `/integrations/gmail/callback` - Completa OAuth
- Salvataggio integrazione in Firestore (`hostEmailIntegrations`)
- Supporto per selezione PMS provider (Scidoo, Booking, Airbnb, Altro)
- Frontend: UI per connessione Gmail con dropdown PMS

### **Step 3: Backfill & Parsing** ✅
- Endpoint `/integrations/gmail/{email}/backfill` - Import storico
- Parser Scidoo (conferme prenotazioni)
- Parser Booking.com (conferme + messaggi)
- Parser Airbnb (conferme + messaggi)
- Query Gmail specifiche per PMS provider
- Deduplica messaggi processati
- Supporto `force=true` per riprocessare email già importate
- Frontend: Loading bar durante import

### **Step 4: Persistenza Automatica** ✅ **APPENA COMPLETATO**
- Repository `PropertiesRepository` - Salva properties in `properties/` (collection root)
- Repository `ClientsRepository` - Salva clienti in `clients/` (collection root)
- Repository `ReservationsRepository` - Salva prenotazioni in `reservations/` (collection root)
- Service `PersistenceService` - Orchestrazione salvataggio
- Linking automatico: reservations → propertyId + clientId, clients → propertyId + reservationId
- Estrazione property name da "Camera/Alloggio" (non "Struttura Richiesta")
- Logging dettagliato per debug

**Struttura Firestore corretta:**
- `properties/{propertyId}` con campo `hostId`
- `clients/{clientId}` con campi `assignedHostId`, `assignedPropertyId`, `reservationId`
- `reservations/{reservationId}` con campi `hostId`, `propertyId`, `clientId`

---

## ⏳ PROSSIMI PASSI (Step 5-8)

### **Step 5: Gmail Watch** ⏳ Priorità MEDIA

**Obiettivo:** Monitorare nuove email in tempo reale tramite Gmail Watch API

**Cosa serve implementare:**

1. **Endpoint Setup Watch**
   - `POST /integrations/gmail/{email}/watch`
   - Chiama Gmail API `users().watch()` per l'email
   - Configura Pub/Sub topic: `projects/{projectId}/topics/gmail-notifications-giovi-ai`
   - Salva subscription info in Firestore (`hostEmailIntegrations/{email}.watchSubscription`)
   - Watch scade dopo 7 giorni → serve refresh automatico

2. **Endpoint Notifiche Pub/Sub**
   - `POST /integrations/gmail/notifications` (pubblico, senza auth - Google verifica firma)
   - Riceve notifiche push da Google Pub/Sub
   - Decodifica payload base64: `{emailAddress, historyId}`
   - Processa nuove email (parsing + persistenza) in background
   - Risponde 204 No Content immediatamente (ack a Pub/Sub)

3. **Cloud Scheduler Job**
   - Refresh automatico watch ogni 7 giorni
   - Chiama endpoint setup watch per ogni integrazione attiva

4. **Configurazione GCP**
   - Creare Pub/Sub topic `gmail-notifications-giovi-ai`
   - Configurare push subscription con webhook URL
   - Permessi: Service account deve poter pubblicare su Pub/Sub

**Note Tecniche:**
- Watch richiede topic Pub/Sub esistente
- Watch scade dopo 7 giorni (limite Gmail)
- Notifiche contengono solo `historyId`, non i messaggi → serve chiamare `history.list()`
- Verificare firma JWT delle notifiche Pub/Sub (Google le firma)

**Riferimenti:**
- Esempio implementazione in `gemini-proxy-service/lib/server.js` (funzione `setupGmailWatch`)
- Documentazione Gmail Watch: https://developers.google.com/gmail/api/guides/push

---

### **Step 6: Pipeline Messaggi Guest** ⏳ Priorità MEDIA

**Obiettivo:** Identificare messaggi guest e preparare contesto per AI

**Cosa serve implementare:**

1. **Service Processamento Notifiche**
   - `EmailNotificationService.process_notification(email_address, history_id)`
   - Chiama Gmail API `history.list()` per ottenere nuovi messaggi
   - Filtra solo messaggi guest (Booking/Airbnb) usando parser esistenti
   - Per ogni messaggio guest:
     - Identifica tipo (conferma vs messaggio)
     - Estrae reservation ID / thread ID
     - Trova prenotazione collegata in Firestore
     - Trova cliente collegato in Firestore
     - Verifica `autoReplyEnabled` del cliente

2. **Verifica Auto-Reply**
   - Query Firestore: `clients/{clientId}.autoReplyEnabled`
   - Se `false` → skip (non rispondere)
   - Se `true` o `undefined` → procedi con AI

3. **Estrazione Contesto**
   - Property: Dati da `properties/{propertyId}`
   - Prenotazione: Dati da `reservations/{reservationId}`
   - Conversazione: Storia messaggi da Gmail (thread) o Firestore
   - Cliente: Dati da `clients/{clientId}`

4. **Pubblicazione Evento**
   - Pubblica evento Pub/Sub: `chat.request` con contesto completo
   - Oppure chiama direttamente Gemini service (se monolitico)

**Note Tecniche:**
- Per Booking: reservation ID è nel subject/body
- Per Airbnb: thread ID identifica conversazione
- Storia conversazione: Gmail API `messages.list()` con `threadId`

---

### **Step 7: Integrazione Gemini AI** ⏳ Priorità MEDIA

**Obiettivo:** Generare risposte AI usando Gemini con contesto completo

**Cosa serve implementare:**

1. **Service Gemini**
   - `GeminiService.generate_response(prompt, context)`
   - Configurazione API key (Secret Manager o env var)
   - Chiamata a Gemini API (REST o SDK)
   - Gestione errori e retry

2. **Costruzione Prompt**
   - Template prompt con contesto dinamico:
     ```
     Sei "Giovi AI", un assistente concierge virtuale amichevole, preciso e disponibile 
     per l'alloggio chiamato "${propertyData.name}".
     
     Contesto:
     - Property: ${propertyData}
     - Prenotazione: ${reservationData}
     - Cliente: ${clientData}
     - Storia conversazione: ${conversationHistory}
     
     Il tuo compito è:
     - Se la domanda è informativa e l'informazione è presente nel contesto fornito, rispondi in modo completo.
     - Se l'informazione richiesta NON è presente o è incompleta: Rispondi: "Mi dispiace, non ho questa informazione specifica nei dettagli forniti dall'host." NON inventare dettagli.
     - Se la domanda è ambigua, chiedi gentilmente di specificare meglio.
     - Se hai già risposto a domande simili nelle conversazioni precedenti, puoi fare riferimento a quelle risposte per mantenere coerenza.
     
     Rispondi in modo cortese e con frasi complete.
     ```

3. **Gestione Conversazioni**
   - Salvare storia conversazione in Firestore (`aiConversations/{conversationId}`)
   - Include: messaggi guest, risposte AI, metadata

4. **Salvataggio Risposte**
   - Salvare risposta AI in Firestore prima di inviare
   - Collection: `aiResponses/{responseId}` o `aiConversations/{conversationId}/messages`

**Note Tecniche:**
- Usare Gemini 1.5 Pro o Flash per costi/performance
- Limitare lunghezza prompt (contesto può essere grande)
- Gestire rate limiting API

**Riferimenti:**
- Esempio in `core-service/src/workflows/aiConversations.ts` (funzione `handleChatRequest`)

---

### **Step 8: Invio Email Reply** ⏳ Priorità MEDIA

**Obiettivo:** Inviare risposta AI come email reply tramite Gmail API

**Cosa serve implementare:**

1. **Metodo Send Reply in GmailService**
   - `GmailService.send_reply(integration, original_message_id, reply_text)`
   - Costruisce email reply con:
     - `In-Reply-To` header (originale)
     - `References` header (thread)
     - `Thread-Id` per Airbnb (se necessario)
   - Chiama Gmail API `messages.send()`

2. **Threading Email**
   - Booking: Usa `In-Reply-To` e `References`
   - Airbnb: Usa `Thread-Id` specifico (da email originale)

3. **Tracking Messaggi Inviati**
   - Salvare in Firestore: `sentReplies/{messageId}`
   - Evitare risposte duplicate (verifica prima di inviare)

4. **Salvataggio Risposta AI**
   - Aggiornare `aiResponses/{responseId}` con `sentAt` timestamp
   - Link a messaggio originale e prenotazione

**Note Tecniche:**
- Gmail API richiede formato MIME per email
- Threading importante per mantenere conversazione organizzata
- Verificare che email non sia già stata risposta (evitare loop)

---

## 🏗️ ARCHITETTURA COMPLETA (Step 5-8)

```
┌─────────────────────────────────────────────────────────────┐
│                    Gmail Watch Flow                         │
└─────────────────────────────────────────────────────────────┘

1. Setup Watch (Step 5)
   Frontend → POST /integrations/gmail/{email}/watch
   ↓
   email-agent-service → Gmail API users().watch()
   ↓
   Salva subscription in Firestore

2. Nuova Email Arriva
   Gmail → Pub/Sub Topic → Webhook
   ↓
   POST /integrations/gmail/notifications
   ↓
   EmailNotificationService.process_notification()
   ↓
   Gmail API history.list() → nuovi messaggi
   ↓
   Parser identifica tipo email
   ↓
   Step 6: Pipeline Messaggi Guest
   ├─ Trova prenotazione/cliente in Firestore
   ├─ Verifica autoReplyEnabled
   └─ Estrae contesto (property, reservation, conversation)
   ↓
   Step 7: Integrazione Gemini AI
   ├─ Costruisce prompt con contesto
   ├─ Chiama Gemini API
   └─ Genera risposta AI
   ↓
   Step 8: Invio Email Reply
   ├─ Costruisce email reply (threading)
   ├─ Gmail API messages.send()
   └─ Salva risposta in Firestore
```

---

## 📋 CHECKLIST IMPLEMENTAZIONE

### Step 5: Gmail Watch
- [ ] Creare Pub/Sub topic `gmail-notifications-giovi-ai` in GCP
- [ ] Implementare `POST /integrations/gmail/{email}/watch`
- [ ] Implementare `POST /integrations/gmail/notifications`
- [ ] Verificare firma JWT notifiche Pub/Sub
- [ ] Salvare subscription info in Firestore
- [ ] Cloud Scheduler job per refresh watch (7 giorni)
- [ ] Test end-to-end: nuova email → notifica → processing

### Step 6: Pipeline Messaggi Guest
- [ ] Service `EmailNotificationService`
- [ ] Metodo `process_notification()`
- [ ] Estrazione reservation ID / thread ID
- [ ] Query Firestore per prenotazione/cliente
- [ ] Verifica `autoReplyEnabled`
- [ ] Estrazione contesto (property, reservation, conversation)
- [ ] Test con email reali

### Step 7: Integrazione Gemini AI
- [ ] Configurazione Gemini API key
- [ ] Service `GeminiService`
- [ ] Costruzione prompt dinamico
- [ ] Chiamata Gemini API
- [ ] Salvataggio risposte in Firestore
- [ ] Gestione errori e retry
- [ ] Test generazione risposte

### Step 8: Invio Email Reply
- [ ] Metodo `GmailService.send_reply()`
- [ ] Costruzione email reply (MIME)
- [ ] Threading (In-Reply-To, References, Thread-Id)
- [ ] Tracking messaggi inviati
- [ ] Salvataggio risposta inviata
- [ ] Test invio email reali

---

## 📚 DOCUMENTAZIONE DISPONIBILE

1. **STATO_PROGETTO.md** - Stato attuale (Step 1-3 completati, Step 4-8 da fare)
   - ⚠️ **AGGIORNARE**: Step 4 è ora completato!

2. **FLUSSO_COMPLETO.md** - Flusso tecnico dettagliato
   - Descrive flussi OAuth, Backfill, Parsing
   - ⚠️ **AGGIORNARE**: Aggiungere flusso persistenza

3. **FIRESTORE_STRUCTURE.md** - Struttura database
   - ✅ **AGGIORNATO**: Include properties, clients, reservations

4. **AI_Email_Agent_Service_Tech_Design.md** - Design tecnico originale
   - Contiene architettura prevista per Step 5-8

5. **Esempi Codice Esistenti:**
   - `gemini-proxy-service/lib/server.js` - Esempio Gmail Watch
   - `core-service/src/workflows/aiConversations.ts` - Esempio Gemini AI
   - `core-service/src/transport/pubsub/index.ts` - Esempio Pub/Sub handler

---

## 🎯 PRIORITÀ IMPLEMENTAZIONE

1. **Step 5 (Gmail Watch)** - Abilita monitoraggio real-time
2. **Step 6 (Pipeline Messaggi)** - Identifica e prepara messaggi guest
3. **Step 7 (Gemini AI)** - Genera risposte intelligenti
4. **Step 8 (Invio Reply)** - Completa il ciclo automatico

**Nota:** Step 5-8 sono interdipendenti ma possono essere implementati in sequenza.

---

## ❓ DOMANDE APERTE

1. **Architettura Monolitica vs Microservizi:**
   - Step 7-8: Integrare in `email-agent-service` o usare `core-service` esistente?
   - `core-service` ha già `handleChatRequest` e integrazione Gemini
   - Opzione: `email-agent-service` pubblica evento Pub/Sub → `core-service` gestisce AI

2. **Gestione Errori:**
   - Cosa fare se Gemini fallisce? Rispondere comunque o skip?
   - Retry policy per Gmail API?
   - Dead letter queue per notifiche fallite?

3. **Rate Limiting:**
   - Limiti Gmail API (quota requests)
   - Limiti Gemini API (tokens/minuto)
   - Gestione throttling

4. **Testing:**
   - Come testare Gmail Watch senza email reali?
   - Mock Pub/Sub notifications?
   - Test end-to-end con account di test?

---

**Ultimo Aggiornamento:** 14 Novembre 2025  
**Prossimo Step:** Step 5 - Gmail Watch

