# 🔄 Flusso Completo e Test - Spiegazione Dettagliata

## 📋 PANORAMICA DEL SISTEMA

Abbiamo sviluppato **Step 1-3** di un sistema per automatizzare il customer care tramite email per property manager.

## ✅ COSA È STATO SVILUPPATO (Dovrebbe Funzionare)

### **Step 1: Setup Base** ✅
- ✅ Servizio FastAPI configurato su `http://localhost:8000`
- ✅ Integrazione Firebase/Firestore
- ✅ Health check: `GET /health/live`
- ✅ CORS configurato per frontend

### **Step 2: OAuth Gmail** ✅ (Dovrebbe Funzionare)
- ✅ `POST /integrations/gmail/start` - Inizia flusso OAuth
- ✅ `POST /integrations/gmail/callback` - Completa OAuth
- ✅ Cifratura token (Fernet)
- ✅ Salvataggio in Firestore: `hostEmailIntegrations/{email}`

### **Step 3: Backfill & Parsing** ✅ (Dovrebbe Funzionare)
- ✅ `POST /integrations/gmail/{email}/backfill?host_id={hostId}` - Import storico
- ✅ Parser Booking.com (conferme + messaggi)
- ✅ Parser Airbnb (conferme + messaggi)
- ✅ Deduplica: `processedMessageIds`

### **Frontend** ✅
- ✅ Pagina `/impostazioni` con `GmailIntegrationCard`
- ✅ Pagina callback: `/integrations/gmail/callback`
- ✅ Integrazione completa con backend

## 🔄 FLUSSO COMPLETO - Cosa Dovrebbe Funzionare

### **1. FLUSSO OAUTH GMAIL** ✅ (Dovrebbe Funzionare)

**Passi:**
1. Utente va su `http://localhost:8080/impostazioni`
2. Inserisce email Gmail nel campo "Indirizzo Gmail"
3. Clicca "Collega Gmail"
4. Frontend chiama `POST http://localhost:8000/integrations/gmail/start` con:
   ```json
   {
     "hostId": "user-uid",
     "email": "nome@gmail.com",
     "redirectUri": "http://localhost:8080/integrations/gmail/callback"
   }
   ```
5. Backend genera URL OAuth Google e salva state in Firestore (`oauthStates/{state}`)
6. Frontend apre popup con URL Google OAuth
7. Utente autorizza accesso Gmail su Google
8. Google reindirizza a `http://localhost:8080/integrations/gmail/callback?code=...&state=...`
9. Frontend chiama `POST http://localhost:8000/integrations/gmail/callback` con:
   ```json
   {
     "state": "...",
     "code": "...",
     "hostId": "user-uid",
     "email": "nome@gmail.com"
   }
   ```
10. Backend:
    - Verifica state
    - Scambia code per access/refresh token
    - Cifra token con Fernet
    - Salva in Firestore: `hostEmailIntegrations/{email}` con:
      - `hostId`: user-uid
      - `emailAddress`: nome@gmail.com
      - `status`: "connected"
      - `encryptedAccessToken`: token cifrato
      - `encryptedRefreshToken`: refresh token cifrato
11. Frontend mostra "Email collegata" ✅

**Cosa dovresti vedere:**
- ✅ Popup OAuth si apre
- ✅ Autorizzazione completata
- ✅ Card mostra "Email collegata" con stato verde
- ✅ In Firestore: documento `hostEmailIntegrations/{email}`

**⚠️ PROBLEMA POSSIBILE: "Il file non si aggiorna"**
- Il componente `GmailIntegrationCard` usa `useGmailIntegration` che fa query Firestore: `where('hostId', '==', hostId)`
- Dopo OAuth, il documento viene salvato con `doc(collection, email)` e campo `hostId`
- Se l'`hostId` nel frontend NON corrisponde all'`hostId` salvato, la query non trova il documento!
- **Verifica**: controlla che `hostId` nel frontend corrisponda all'`hostId` usato nel backend OAuth callback

### **2. FLUSSO BACKFILL EMAIL** ✅ (Dovrebbe Funzionare)

**Passi:**
1. Utente ha già collegato Gmail (OAuth completato)
2. Clicca "Importa email prenotazioni" nella card Gmail
3. Frontend chiama: `POST http://localhost:8000/integrations/gmail/{email}/backfill?host_id={hostId}`
4. Backend:
   - Recupera integrazione da Firestore: `hostEmailIntegrations/{email}`
   - Decifra token
   - Chiama Gmail API per ultimi 6 mesi: `from:(@mchat.booking.com OR @reply.airbnb.com OR reservation@scidoo.com OR automated@airbnb.com)`
   - Per ogni email:
     - Verifica se già processata: `processedMessageIds/{messageId}`
     - Se non processata:
       - Passa ai parser (Booking/Airbnb)
       - Estratte info prenotazione/messaggio
       - Marca come processata: `processedMessageIds/{messageId}`
5. Backend restituisce:
   ```json
   {
     "processed": 15,
     "items": [
       {
         "kind": "booking_confirmation",
         "reservation": { ... },
         "metadata": { ... }
       },
       ...
     ]
   }
   ```
6. Frontend mostra toast: "Import completato. Processate X email" ✅

**Cosa dovresti vedere:**
- ✅ Toast "Import completato"
- ✅ In console backend: log di email processate
- ✅ In Firestore: sottocollezione `processedMessageIds/{email}/{messageId}`

**⚠️ NOTA:** Il parsing funziona ma i dati **NON vengono salvati automaticamente** in `reservations`, `clients`, `properties`. Questo è Step 4 (non ancora implementato).

### **3. FLUSSO PARSING EMAIL** ✅ (Dovrebbe Funzionare)

**Email Booking.com Conferma:**
- ✅ Estrae: `reservationId`, `propertyName`, `checkIn`, `checkOut`, `guestName`, `guestEmail`, `totalAmount`
- ✅ Tipo: `booking_confirmation`

**Email Booking.com Messaggio:**
- ✅ Estrae: `reservationId`, `message`, `replyTo`
- ✅ Tipo: `booking_message`

**Email Airbnb Conferma:**
- ✅ Estrae: `threadId`, `propertyName`, `checkIn`, `checkOut`, `guestName`, `guestEmail`, `totalAmount`
- ✅ Tipo: `airbnb_confirmation`

**Email Airbnb Messaggio:**
- ✅ Estrae: `threadId`, `message`, `guestName`, `replyTo`
- ✅ Tipo: `airbnb_message`

**⚠️ NOTA:** Il parsing estrae i dati ma **NON li salva** in Firestore. Questo è Step 4.

## ❌ COSA NON È ANCORA IMPLEMENTATO (Step 4-8)

### **Step 4: Persistenza Automatica** ❌
- ❌ Salvataggio prenotazioni in `reservations`
- ❌ Salvataggio clienti in `clients`
- ❌ Salvataggio property in `properties`
- **Stato attuale:** Il parsing funziona ma i dati non vengono salvati in Firestore

### **Step 5: Gmail Watch** ❌
- ❌ Setup Gmail watch per notifiche real-time
- ❌ Endpoint per gestire notifiche Pub/Sub da Gmail
- ❌ Refresh automatico watch (ogni 7 giorni)

### **Step 6: Pipeline Messaggi Guest** ❌
- ❌ Rilevamento messaggi guest in tempo reale
- ❌ Verifica `autoReplyEnabled` per cliente
- ❌ Estrazione contesto conversazione

### **Step 7: Integrazione Gemini AI** ❌
- ❌ Chiamata a Gemini per generare risposte
- ❌ Costruzione prompt con contesto
- ❌ Gestione conversazioni

### **Step 8: Invio Email Reply** ❌
- ❌ Invio email reply tramite Gmail API
- ❌ Salvataggio risposte AI in Firestore
- ❌ Tracking messaggi inviati

## 🐛 RISOLUZIONE: "Il file non si aggiorna"

Il problema è che `GmailIntegrationCard` usa una query Firestore: `where('hostId', '==', hostId)`.

**Possibili cause:**
1. **hostId non corrisponde**: L'`hostId` usato nel frontend non corrisponde all'`hostId` usato nel backend OAuth callback
2. **Documento non salvato**: Il documento non viene salvato correttamente in Firestore
3. **Listener non attivo**: Il listener Firestore non si attiva

**Verifica:**
- Controlla Firestore Console: esiste `hostEmailIntegrations/{email}`?
- Controlla console browser (F12): ci sono errori?
- Controlla `hostId`: è corretto sia nel frontend che nel backend?

## 🧪 TEST COMPLETO - Checklist

### **Test 1: OAuth Flow** ✅ (Dovrebbe Funzionare)
- [ ] Vai su `/impostazioni`
- [ ] Inserisci email Gmail
- [ ] Clicca "Collega Gmail"
- [ ] Popup OAuth si apre
- [ ] Autorizzazione completata
- [ ] Card mostra "Email collegata"
- [ ] Firestore contiene `hostEmailIntegrations/{email}`

### **Test 2: Backfill** ✅ (Dovrebbe Funzionare)
- [ ] Click "Importa email prenotazioni"
- [ ] Toast "Import completato"
- [ ] Backend log mostra email processate (`/tmp/backend.log`)
- [ ] Firestore contiene `processedMessageIds/{email}/{messageId}`

### **Test 3: Parsing** ✅ (Dovrebbe Funzionare)
- [ ] Email Booking conferma → parser estrae dati
- [ ] Email Booking messaggio → parser estrae dati
- [ ] Email Airbnb conferma → parser estrae dati
- [ ] Email Airbnb messaggio → parser estrae dati

### **Test 4: Persistenza** ❌ (NON Funziona)
- [ ] Prenotazioni salvate in `reservations` ❌
- [ ] Clienti salvati in `clients` ❌
- [ ] Property salvate in `properties` ❌

### **Test 5: Watch** ❌ (NON Funziona)
- [ ] Gmail watch attivo ❌
- [ ] Nuove email triggerano notifica ❌

### **Test 6: AI Reply** ❌ (NON Funziona)
- [ ] Messaggio guest → verifica autoReplyEnabled ❌
- [ ] Chiamata Gemini ❌
- [ ] Invio risposta ❌

## 📊 STATO SERVIZI

- ✅ **Backend**: `http://localhost:8000` - Log: `/tmp/backend.log`
- ✅ **Frontend**: `http://localhost:8080` - Log: `/tmp/frontend.log`

Posso vedere i log in tempo reale! 🎉

