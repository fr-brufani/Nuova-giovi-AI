# 📋 Checklist Test Completi - Email Agent Service

## ✅ Già Testato e Funzionante

- [x] **Step 1-4: Setup Base**
  - [x] OAuth Gmail integration
  - [x] Backfill email storiche
  - [x] Parsing email (Scidoo, Booking, Airbnb)
  - [x] Salvataggio in Firestore (properties, reservations, clients)

- [x] **Step 5: Gmail Watch Setup**
  - [x] Attivazione watch dal frontend
  - [x] Salvataggio watchSubscription in Firestore
  - [x] Status aggiornato ad "active"

---

## 🔴 DA TESTARE - Flusso Completo End-to-End

### 📧 Test 1: Ricezione Notifica Gmail Watch

**Obiettivo:** Verificare che quando arriva una nuova email, Gmail invii la notifica al servizio.

**Come testare:**
1. Invia un'email test alla casella Gmail collegata (`shortdeseos@gmail.com`)
2. Email da testare:
   - **Scidoo conferma:** Da `reservation@scidoo.com` con subject "Confermata - Prenotazione"
   - **Booking message:** Da `@guest.booking.com`
   - **Airbnb message:** Da `express@airbnb.com`

**Verifiche:**
- [ ] Pub/Sub riceve la notifica (entro 1-2 minuti)
- [ ] Log Cloud Run mostrano: `[WATCH] 📧 Nuova email ricevuta: [messageId]`
- [ ] Notifica viene processata senza errori

**Comandi:**
```bash
# Monitora log in tempo reale
gcloud run services logs read email-agent-service \
  --region europe-west1 \
  --project giovi-ai \
  --limit 100 \
  --follow

# Verifica Pub/Sub
gcloud pubsub subscriptions describe gmail-notifications-subscription \
  --project giovi-ai
```

---

### 🔍 Test 2: Filtro Email (Solo Rilevanti)

**Obiettivo:** Verificare che solo email rilevanti vengano processate.

**Come testare:**
1. Invia email NON rilevanti:
   - Email normale da amico/famiglia
   - Newsletter
   - Email promozionali

**Verifiche:**
- [ ] Email non rilevanti vengono **ignorate** (no log di processamento)
- [ ] Solo email da `reservation@scidoo.com` (se `pmsProvider=scidoo`) vengono processate
- [ ] Solo messaggi guest da `@guest.booking.com` o `express@airbnb.com` vengono processati

**Cosa verificare nei log:**
```
[WATCH] ⚠️ Email non rilevante, ignorata: [email]
```

---

### 💾 Test 3: Parsing e Salvataggio Email Rilevanti

**Obiettivo:** Verificare che le email rilevanti vengano parsate e salvate correttamente.

**Come testare:**
1. Invia email di conferma Scidoo (`reservation@scidoo.com` - "Confermata - Prenotazione")
2. Invia messaggio guest Booking (`@guest.booking.com`)

**Verifiche per Email Conferma:**
- [ ] Email viene parsata correttamente (`scidoo_confirmation`)
- [ ] Property creata/aggiornata in `properties`
- [ ] Client creato/aggiornato in `clients`
- [ ] Reservation creata/aggiornata in `reservations`
- [ ] Log: `[WATCH] ✅ Email salvata: [messageId]`

**Verifiche per Messaggio Guest:**
- [ ] Email viene parsata correttamente (`booking_message` o `airbnb_message`)
- [ ] Messaggio salvato in `properties/{propertyId}/conversations/{clientId}/messages`
- [ ] Log: `[WATCH] 📧 Messaggio guest salvato`

**Comandi:**
```bash
# Verifica Firestore dopo invio email
# Properties
gcloud firestore documents list --collection-id=properties --project giovi-ai --limit 5

# Reservations
gcloud firestore documents list --collection-id=reservations --project giovi-ai --limit 5

# Clients
gcloud firestore documents list --collection-id=clients --project giovi-ai --limit 5
```

---

### 🤖 Test 4: AI Reply Generation (Step 7)

**Obiettivo:** Verificare che quando arriva un messaggio guest, l'AI generi una risposta.

**Prerequisiti:**
- [ ] Client deve esistere in `clients`
- [ ] `autoReplyEnabled` deve essere `true` (default)
- [ ] Reservation deve esistere in `reservations`
- [ ] Property deve esistere in `properties`

**Come testare:**
1. Assicurati che ci sia un client con `autoReplyEnabled: true`
2. Invia un messaggio guest a quel client

**Verifiche:**
- [ ] Log: `[WATCH] 📧 Messaggio guest pronto per AI reply: clientId=..., reservationId=...`
- [ ] Log: `[GEMINI] ✅ Risposta AI generata ([X] caratteri)`
- [ ] Risposta AI salvata in Firestore: `properties/{propertyId}/conversations/{clientId}/messages`
- [ ] Log: `[WATCH] Risposta AI salvata in conversazione`

**Cosa verificare nei log:**
```
[WATCH] 📧 Messaggio guest pronto per AI reply: clientId=xxx, reservationId=yyy
[GEMINI] ✅ Risposta AI generata (234 caratteri)
[WATCH] Risposta AI salvata in conversazione: property=zzz, client=xxx
```

**Firestore - Verifica risposta AI:**
```json
// properties/{propertyId}/conversations/{clientId}/messages/{messageId}
{
  "sender": "host_ai",
  "text": "Risposta generata da Gemini AI...",
  "timestamp": Timestamp(now),
  "source": "ai_reply",
  "gmailMessageId": "...",
  "replyMessageId": "...",
  "reservationId": "...",
  "guestMessage": "Messaggio originale guest..."
}
```

---

### 📨 Test 5: Invio Email Risposta (Step 8)

**Obiettivo:** Verificare che la risposta AI venga inviata correttamente via Gmail API.

**Come testare:**
1. Dopo che l'AI ha generato la risposta (Test 4)

**Verifiche:**
- [ ] Email risposta inviata via Gmail API
- [ ] Log: `[WATCH] ✅ Email risposta inviata: messageId=..., threadId=...`
- [ ] Threading corretto (Reply-To, In-Reply-To, References)
- [ ] Email ricevuta nella casella Gmail del guest
- [ ] Email è una risposta al thread originale

**Cosa verificare nei log:**
```
[WATCH] ✅ Email risposta inviata: messageId=xxx, threadId=yyy
```

**Verifica manuale:**
- Controlla la casella email del guest
- Verifica che la risposta sia nel thread corretto
- Verifica che il subject sia "Re: [subject originale]"

---

### 🔄 Test 6: Flusso Completo End-to-End

**Obiettivo:** Testare tutto il flusso da email ricevuta a risposta inviata.

**Scenario completo:**
1. **Invia email conferma Scidoo** → Verifica salvataggio property/reservation/client
2. **Invia messaggio guest** → Verifica:
   - Messaggio salvato
   - AI reply generata
   - Risposta inviata
   - Tutto salvato in Firestore

**Verifiche finali:**
- [ ] Property creata con nome corretto
- [ ] Reservation creata con dati corretti
- [ ] Client creato/aggiornato
- [ ] Messaggio guest salvato in conversazione
- [ ] Risposta AI generata e salvata
- [ ] Email risposta inviata al guest
- [ ] Threading email corretto

---

### ⚠️ Test 7: Edge Cases e Error Handling

**Test vari scenari:**

1. **Client con autoReplyEnabled = false:**
   - [ ] Messaggio ricevuto ma AI reply NON generata
   - [ ] Log: `[PIPELINE] Auto-reply disabilitato per cliente xxx`

2. **Messaggio senza reservation associata:**
   - [ ] Messaggio salvato ma AI reply NON generata
   - [ ] Log di warning appropriato

3. **Watch scaduto:**
   - [ ] Verifica che dopo 7 giorni il watch non funzioni
   - [ ] Rinnova watch e verifica che riprenda a funzionare

4. **Email duplicata:**
   - [ ] Email già processata viene ignorata
   - [ ] Log: `[WATCH] ⚠️ Email già processata, skip`

---

## 📊 Metriche da Monitorare

### Durante i test, monitora:

1. **Tempo di risposta:**
   - Notifica → Processamento: < 2 minuti
   - Messaggio → AI Reply: < 10 secondi
   - AI Reply → Email inviata: < 2 secondi

2. **Errori:**
   - Zero errori 500
   - Warning accettabili solo per email non rilevanti

3. **Firestore:**
   - Tutti i dati salvati correttamente
   - Nessun documento duplicato
   - Relazioni corrette (reservationId, propertyId, clientId)

---

## 🚀 Ordine Consigliato per i Test

1. **Test 1:** Ricezione notifica (email test semplice)
2. **Test 2:** Filtro email (verifica che email non rilevanti siano ignorate)
3. **Test 3:** Parsing e salvataggio (email conferma Scidoo)
4. **Test 4:** AI Reply (messaggio guest)
5. **Test 5:** Invio email (verifica risposta inviata)
6. **Test 6:** Flusso completo end-to-end
7. **Test 7:** Edge cases

---

## 🔧 Comandi Utili per il Testing

### Monitora tutto in tempo reale:
```bash
# Log Cloud Run
gcloud run services logs read email-agent-service \
  --region europe-west1 \
  --project giovi-ai \
  --limit 200 \
  --follow

# Filtra solo log WATCH
gcloud run services logs read email-agent-service \
  --region europe-west1 \
  --project giovi-ai \
  --limit 200 \
  --follow | grep "WATCH\|GEMINI\|PIPELINE"
```

### Verifica stato Firestore:
```bash
# Watch subscription
gcloud firestore documents get \
  projects/giovi-ai/databases/(default)/documents/hostEmailIntegrations/shortdeseos@gmail.com \
  --project giovi-ai

# Properties
gcloud firestore documents list --collection-id=properties --project giovi-ai

# Reservations
gcloud firestore documents list --collection-id=reservations --project giovi-ai

# Clients
gcloud firestore documents list --collection-id=clients --project giovi-ai
```

### Health check servizio:
```bash
curl "https://email-agent-service-228376111127.europe-west1.run.app/health/live"
```

---

## ✅ Criteri di Successo

Tutti i test sono passati quando:

1. ✅ Gmail Watch riceve notifiche correttamente
2. ✅ Solo email rilevanti vengono processate
3. ✅ Email vengono parsate e salvate correttamente
4. ✅ AI genera risposte quando `autoReplyEnabled=true`
5. ✅ Risposte vengono inviate correttamente via email
6. ✅ Threading email è corretto
7. ✅ Tutti i dati sono salvati in Firestore
8. ✅ Nessun errore critico nei log

---

## 📝 Note

- **Tempo atteso notifiche:** Gmail può richiedere 1-2 minuti per inviare notifiche
- **Rate limiting:** Gmail API ha limiti di rate, aspetta tra un test e l'altro
- **Test con email reali:** Usa email reali per test completi (non mock)
- **Verifica manuale:** Controlla manualmente le email inviate ai guest

